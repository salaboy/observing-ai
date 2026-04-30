package com.example.store.tracing;

import jakarta.annotation.PostConstruct;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Hooks;

@Configuration(proxyBeanMethods = false)
public class ContextPropagationConfiguration {
    // This is required since I am not using Spring WebFlux, but I am returning a Flux on the chat
    @PostConstruct
    void enableReactorContextPropagation() {
        Hooks.enableAutomaticContextPropagation();  // bridges ThreadLocal → Reactor Context
    }
}
