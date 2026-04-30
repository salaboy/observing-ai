# Observing Spring AI Applications with OpenTelemetry

AI applications behave differently from traditional REST services. A user sends a message, and internally
the application may call a language model, retrieve memory from a previous turn, invoke one or more tools,
and stream a response back — all as part of a single HTTP request. Knowing that a request took 2.6 seconds
tells you very little. Knowing *why* it took that long, which model was used, how many tokens were consumed,
and which tool was called — that is actionable observability.

This post walks through a Spring Boot 4.0 application built with Spring AI, explains what observability
comes for free, what you need to configure, and how to read the resulting traces to understand what your
AI application is actually doing.

---

## The Application: Spring Merch Store

The sample application is a store assistant powered by Anthropic's Claude Haiku model. Users interact with
it via a streaming chat endpoint. The assistant can look up inventory, display product images, and place orders.

```
POST /api/chat/stream   ← user sends a message
```

The core of the application is a `ChatClient` wired up with a system prompt, tools, and a memory advisor:

```java
public ChatRestController(ChatClient.Builder chatClientBuilder, ChatController inventoryTools) {
    this.chatClient = chatClientBuilder
            .defaultSystem(SYSTEM_PROMPT)
            .defaultTools(inventoryTools)
            .build();
}

@PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<String> chatStream(@RequestBody ChatRequest request) {
    MessageChatMemoryAdvisor advisor = MessageChatMemoryAdvisor.builder(
                    MessageWindowChatMemory.builder()
                            .chatMemoryRepository(memoryRepository)
                            .build())
            .conversationId(request.conversationId())
            .build();

    return chatClient.prompt()
            .advisors(advisor)
            .user(request.message())
            .stream()
            .content();
}
```

The `ChatController` component exposes four `@Tool`-annotated methods:

| Tool | Description |
|---|---|
| `listAllItems` | Returns full inventory with prices |
| `getItemStock` | Looks up stock for a specific item |
| `displayMerchImages` | Returns product cards for the frontend |
| `placeOrder` | Places a confirmed order |

This is a realistic pattern: a conversational interface backed by a model that decides when to call which
tool based on what the user says.

---

## Setting Up OpenTelemetry in Spring Boot 4

Spring Boot 4 ships `spring-boot-starter-opentelemetry`, which pulls in the full OpenTelemetry SDK,
the Micrometer Tracing bridge, the OTLP span exporter, and the auto-configuration wiring. You do not
need to write any boilerplate to get traces exported.

**`pom.xml`**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-opentelemetry</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

**`application.properties`**
```properties
spring.application.name=spring-merch-store

# Sample every request — use a lower value in high-traffic production
management.tracing.sampling.probability=1.0

# Support both W3C traceparent and B3 propagation headers
management.tracing.propagation.type=W3C,B3

# OTLP/HTTP export endpoint and auth headers
management.opentelemetry.tracing.export.otlp.endpoint=${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces
management.opentelemetry.tracing.export.otlp.headers.Authorization=Bearer ${OTEL_EXPORTER_OTLP_HEADERS_AUTHORIZATION}
management.opentelemetry.tracing.export.otlp.headers.Dash0-Dataset=observing-java

# Expose all actuator endpoints (useful during development)
management.endpoints.web.exposure.include=*
```

A few things worth noting here:

- The `management.opentelemetry.tracing.export.otlp.*` namespace is new in Spring Boot 4. The old
  `management.otlp.tracing.*` keys are removed.
- `Content-Type` must **not** be set in the headers map. The OTLP/HTTP exporter manages
  `Content-Type: application/x-protobuf` internally. Overriding it breaks serialization.
- The `OtlpTracingConnectionDetails` bean only activates when the endpoint property is non-null,
  so both environment variables must be set before starting the application.

### Spring AI observability properties

Spring AI 2.0 gates prompt and completion logging behind explicit flags because these can be sensitive
and high-cardinality:

```properties
# Include full prompt and completion content in span attributes
spring.ai.chat.observations.log-prompt=true
spring.ai.chat.observations.log-completion=true
spring.ai.chat.client.observations.log-prompt=true
spring.ai.chat.client.observations.log-completion=true
spring.ai.tools.observations.include-content=true
```

With these enabled you get the full conversational context visible in every trace, which is invaluable
during development and debugging.

---

## What a Single Chat Request Looks Like as Traces

When a user sends a message that causes the assistant to call a tool, the resulting trace is a hierarchy
of spans that maps exactly onto the Spring AI execution model:

```
http post /api/chat/stream                          ~2.6 s  ← Servlet request
└── spring_ai chat_client                           ~2.6 s  ← ChatClient.stream()
    └── message_chat_memory (advisor)               ~2.6 s  ← MessageChatMemoryAdvisor
        └── stream                                  ~2.6 s  ← Advisor chain
            ├── chat claude-haiku-4-5               ~1.8 s  ← First LLM call (decides to use tool)
            ├── tool_call displayMerchImages         <20 ms  ← Tool execution
            └── chat claude-haiku-4-5               ~1.2 s  ← Second LLM call (generates response)
```

This hierarchy gives you answers that a single latency metric cannot:

- Was the slowness in the HTTP layer, the model, or a tool?
- Which LLM call generated the final response vs. the tool-selection call?
- How long does the memory advisor add to the overall request?

### Reading the span attributes

Each span carries structured attributes following the [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/). The most important ones are:

**On `chat claude-haiku-4-5` spans:**

| Attribute | Example value | What it tells you |
|---|---|---|
| `gen_ai.system` | `anthropic` | Which provider was called |
| `gen_ai.request.model` | `claude-haiku-4-5` | Model requested |
| `gen_ai.response.model` | `claude-haiku-4-5-20251001` | Exact model version served |
| `gen_ai.request.max_tokens` | `4096` | Token budget per request |
| `gen_ai.usage.input_tokens` | `1308–3729` | Tokens in the prompt |
| `gen_ai.usage.output_tokens` | `58–457` | Tokens in the completion |
| `gen_ai.response.finish_reasons` | `["end_turn"]` | Why the model stopped |
| `gen_ai.prompt` | *(full prompt text)* | What was actually sent |
| `gen_ai.completion` | *(full response text)* | What the model returned |

**On `tool_call` spans:**

| Attribute | Example value |
|---|---|
| `spring.ai.tool.definition.name` | `displayMerchImages` |
| `spring.ai.tool.definition.description` | Tool description as registered |
| `spring.ai.tool.call.arguments` | `{"query": "Spring Boot"}` |
| `spring.ai.tool.call.result` | The JSON the tool returned |

**On `spring_ai chat_client` spans:**

| Attribute | Value |
|---|---|
| `spring.ai.kind` | `chat_client` |
| `spring.ai.chat.client.stream` | `true` |
| `spring.ai.model.request.tool.names` | `["placeOrder", "displayMerchImages", "getItemStock", "listAllItems"]` |

**On advisor spans:**

| Attribute | Value |
|---|---|
| `spring.ai.kind` | `advisor` |
| `spring.ai.advisor.name` | `MessageChatMemoryAdvisor` |
| `spring.ai.advisor.order` | `-2147482648` |

---

## Token Usage: The Hidden Cost Dimension

Traditional application monitoring tracks CPU, memory, and network. For AI applications there is a fourth
resource: tokens. Token consumption directly translates to cost, and it varies with every request because
it grows with conversation length.

From the observed traces:

```
Input tokens:   1,308 → 3,729  (conversation grows with each turn)
Output tokens:    58  →   457  (depends on response complexity)
```

The input token growth is not a bug — it is the `MessageChatMemoryAdvisor` appending prior turns to
each request. After a few exchanges the prompt grows from ~1,300 tokens to ~3,700 tokens. Without
traces exposing `gen_ai.usage.input_tokens` you would not see this happening.

Practical thresholds to alert on:

```
gen_ai.usage.input_tokens  > 3000   # approaching model context window, cost rising
gen_ai.usage.output_tokens > 400    # unusually verbose response
span.duration (chat spans) > 4s     # latency SLO breach
```

---

## Making Tool Calls Visible

Tool calls are traced as child spans of the LLM interaction span, which means you can see exactly
which tools were invoked, with what arguments, and what they returned — in sequence.

For the store assistant, a user asking "show me all Spring AI items" triggers:

1. First LLM call — model sees available tools (`listAllItems`, `displayMerchImages`, etc.) in its
   system prompt, decides to call `displayMerchImages("Spring AI")`
2. `tool_call displayMerchImages` — executes in under 20ms, returns a JSON payload
3. Second LLM call — model receives the tool result and generates the final user-facing response

This is visible because Spring AI instruments tool invocations using the `spring.ai.kind=tool_call`
attribute and creates a separate span for each one. The `spring.ai.tool.call.arguments` and
`spring.ai.tool.call.result` attributes (enabled via `spring.ai.tools.observations.include-content=true`)
show the exact data flowing in and out of each tool.

Performance data from real traces:

| Operation | Latency |
|---|---|
| Tool call (any) | < 20 ms |
| Single LLM call | 1.2 – 2.7 s |
| Full chat stream request | ~2.6 – 4.0 s |

Tool calls are negligible in cost. LLM calls dominate. If your traces show the opposite, investigate
whether tools are making external HTTP calls without those calls being traced.

---

## Propagating Trace Context Across HTTP Calls

When a tool or advisor makes an outgoing HTTP call (to a database, a product API, a payment service),
trace context needs to be forwarded so that the remote service's spans appear in the same trace.
Spring Boot's `RestClient` does not do this automatically. The application wires it up explicitly:

```java
@Bean
RestClientCustomizer tracePropagationRestClientCustomizer(OpenTelemetry openTelemetry) {
    return builder -> builder.requestInterceptor((request, body, execution) -> {
        openTelemetry.getPropagators().getTextMapPropagator().inject(
                Context.current(),
                request.getHeaders(),
                (headers, key, value) -> headers.set(key, value)
        );
        return execution.execute(request, body);
    });
}
```

This injects `traceparent` (W3C) and `b3` headers into every `RestClient` request, so that downstream
services can participate in the same distributed trace. Without this, tool spans would appear as isolated
traces with no connection to the originating chat request.

---

## Exposing the Trace ID to Clients

The application includes a servlet filter that writes the current trace ID into the HTTP response:

```java
@Component
class TraceIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws IOException, ServletException {
        String traceId = getTraceId();
        if (traceId != null) {
            response.setHeader("X-Trace-Id", traceId);
        }
        filterChain.doFilter(request, response);
    }
}
```

The frontend receives `X-Trace-Id` in each response. This makes it trivial to correlate a user complaint
("my last request was slow") with the exact trace in your observability backend — no log scraping required.

---

## Adding Prompt and Completion as Span Attributes

Spring AI 2.0 logs prompts and completions to the application log when you set
`spring.ai.chat.observations.log-prompt=true`, but it does not include them as span attributes by default.
The application overrides the default observation convention to promote them into the trace:

```java
@Bean
public ChatModelObservationConvention promptAndCompletionObservationConvention() {
    return new DefaultChatModelObservationConvention() {
        @Override
        public KeyValues getHighCardinalityKeyValues(ChatModelObservationContext context) {
            KeyValues keyValues = super.getHighCardinalityKeyValues(context);

            // Attach full prompt text as a span attribute
            if (!CollectionUtils.isEmpty(context.getRequest().getInstructions())) {
                String prompt = context.getRequest().getInstructions().stream()
                        .map(Content::getText)
                        .collect(Collectors.joining("\n"));
                if (StringUtils.hasText(prompt)) {
                    keyValues = keyValues.and("gen_ai.prompt", prompt);
                }
            }

            // Attach full completion text as a span attribute
            if (context.getResponse() != null && !CollectionUtils.isEmpty(context.getResponse().getResults())) {
                String completion = context.getResponse().getResults().stream()
                        .filter(g -> g.getOutput() != null && StringUtils.hasText(g.getOutput().getText()))
                        .map(g -> g.getOutput().getText())
                        .collect(Collectors.joining("\n"));
                if (StringUtils.hasText(completion)) {
                    keyValues = keyValues.and("gen_ai.completion", completion);
                }
            }

            return keyValues;
        }
    };
}
```

With this in place, every LLM span carries the exact prompt that was sent and the exact text that came back.
This is high-cardinality data — keep it disabled in production unless your observability backend supports
it efficiently and you have a data retention policy for it. During development and debugging it is
extremely useful for understanding why the model responded a certain way.

---

## Observability Checklist for Spring AI Applications

Based on this application, here is what you get without writing any tracing code, and what you need
to configure explicitly:

**Out of the box (zero configuration):**
- HTTP request spans with method, path, status code
- ChatClient spans with streaming/non-streaming flag
- LLM call spans with model name, token counts, finish reason
- Tool call spans with tool name

**Requires configuration properties:**
- Full prompt text in spans (`spring.ai.chat.observations.log-prompt=true`)
- Full completion text in spans (`spring.ai.chat.observations.log-completion=true`)
- Tool arguments and results (`spring.ai.tools.observations.include-content=true`)

**Requires a small amount of application code:**
- Forwarding trace context in outgoing `RestClient` requests
- Returning the trace ID to the caller via response header
- Promoting prompt/completion to span attributes via custom `ChatModelObservationConvention`

**Requires alerting rules in your observability backend:**
- `gen_ai.usage.input_tokens` growth (conversation length / cost management)
- `gen_ai.usage.output_tokens` spikes (unexpectedly long responses)
- LLM span duration > threshold (model latency SLO)
- Tool call span error status (tool failure detection)

---

## Summary

Spring AI and Spring Boot 4 give you a solid observability foundation out of the box via the
OpenTelemetry SDK. The span hierarchy that emerges from a single chat request directly reflects the
Spring AI execution model: `ChatClient` → advisor chain → LLM call → tool calls. Each level carries
structured attributes following the GenAI semantic conventions, which means your dashboards and alerts
can be portable across different AI providers.

The most important things to watch in production are token usage (it grows with conversation length and
drives cost), LLM call duration (it dominates end-to-end latency), and tool call error status (failures
here silently degrade assistant behavior). All three are visible in traces without any custom instrumentation,
as long as you configure the OTLP exporter correctly and point it at a backend that understands
OpenTelemetry.
