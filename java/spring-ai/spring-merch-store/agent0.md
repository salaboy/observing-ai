# Observing Spring AI Applications with OpenTelemetry



## Insights from Agent0

Based on the trace analysis of the
spring-merch-store
application, here are the key findings valuable for Spring Boot and Spring AI developers:

Architecture Overview
The application is a Java-based Spring Boot service implementing an AI-powered store assistant using Spring AI with Anthropic's Claude Haiku model (claude-haiku-4-5-20251001).

Spring AI Integration Insights
1. Instrumentation Hierarchy
   The traces reveal a well-structured Spring AI span hierarchy:

Root: http post /api/chat/stream (HTTP endpoint)
Level 1: spring_ai chat_client (ChatClient component)
Level 2: message_chat_memory (MessageChatMemoryAdvisor)
Level 3: stream (Advisor with streaming)
Level 4: chat claude-haiku-4-5 (LLM interaction)
Separate: tool_call spans (function calling)
2. Key Span Attributes for Monitoring
   Gen AI Attributes (GenAI Semantic Conventions):

gen_ai.system: anthropic
gen_ai.operation.name: chat or framework
gen_ai.request.model: claude-haiku-4-5
gen_ai.response.model: claude-haiku-4-5-20251001
gen_ai.request.max_tokens: 4096
gen_ai.usage.input_tokens: Varies (1308-3729)
gen_ai.usage.output_tokens: Varies (58-457)
gen_ai.usage.total_tokens: Combined token usage
gen_ai.response.finish_reasons: ["end_turn"]
gen_ai.prompt: Full system prompt (visible in traces)
gen_ai.completion: Full response content
Spring AI Specific Attributes:

spring.ai.kind: chat_client, advisor, or tool_call
spring.ai.advisor.name: e.g., MessageChatMemoryAdvisor
spring.ai.advisor.order: e.g., -2147482648
spring.ai.model.request.tool.names: ["placeOrder", "displayMerchImages", "getItemStock", "listAllItems"]
spring.ai.chat.client.advisors: Advisor configuration
spring.ai.chat.client.stream: Streaming configuration
spring.ai.chat.client.tool.names: Tool names
spring.ai.tool.call.arguments: Tool invocation arguments
spring.ai.tool.call.result: Tool execution results
spring.ai.tool.definition.name: Tool name
spring.ai.tool.definition.description: Tool description
spring.ai.tool.definition.schema: Tool JSON schema
3. Performance Characteristics
   Latencies (P95):

Overall request: ~2.8 seconds
Chat stream endpoint: ~2.6 seconds
Individual LLM calls: 1.2-2.7 seconds
Tool calls: <20ms (very fast)
Chat client operations: 2.6-4.0 seconds
Token Usage Patterns:

Input tokens: 1,308-3,729 (varies by conversation context)
Output tokens: 58-457 (depends on response complexity)
Token costs are automatically tracked per request
4. Operational Insights
   Operations Detected:

http post /api/chat/stream - Main streaming chat endpoint
tool_call displayMerchImages - Display product images
tool_call placeOrder - Order placement
http get /api/config - Configuration endpoint
http get /** - Static resources
Health Status: All operations show healthy status with no errors detected.

5. Observability Best Practices Implemented
   ✅ Full GenAI semantic conventions - Proper use of gen_ai.* attributes
   ✅ Spring AI telemetry - Rich spring.ai.* attributes for advisors, tools, and chat client
   ✅ Streaming traces - Streaming operations are properly instrumented
   ✅ Function calling visibility - Tool calls tracked as separate spans
   ✅ Token usage tracking - Input/output tokens captured for cost analysis
   ✅ Memory advisor tracking - Chat memory operations are visible

6. Recommendations for Developers
   For Development:

Monitor token usage trends - Input tokens vary significantly (1,308-3,729), indicating conversation context growth
Track tool call patterns - 4 tools available: placeOrder, displayMerchImages, getItemStock, listAllItems
Analyze advisor chains - MessageChatMemoryAdvisor is applied with order -2147482648
Response time optimization - LLM calls take 1.2-2.7s; consider caching or streaming improvements
For Operations:

Set up alerts on:

gen_ai.usage.input_tokens > threshold (context window management)
gen_ai.usage.output_tokens > threshold (cost management)
otel.span.duration for chat operations > 5s (latency SLO)
Tool call failures (error status on tool_call spans)
Dashboard metrics:

Token consumption rate (input + output)
Model response times by operation
Tool call success rate
Advisor execution times
Cost monitoring:

Track gen_ai.usage.total_tokens aggregated over time
Monitor token-to-cost conversion based on Claude pricing
For Debugging:

All prompts and completions are captured in traces (gen_ai.prompt, gen_ai.completion)
Tool definitions and invocations are fully traced
Request/response IDs available (gen_ai.response.id)
7. Technology Stack Confirmed
   Runtime: Java (OpenTelemetry Java SDK)
   Framework: Spring Boot with Spring AI
   LLM Provider: Anthropic (Claude Haiku 4.5)
   Pattern: Streaming chat with function calling and memory advisors
   This application demonstrates production-ready Spring AI instrumentation with comprehensive observability for AI-powered applications.**