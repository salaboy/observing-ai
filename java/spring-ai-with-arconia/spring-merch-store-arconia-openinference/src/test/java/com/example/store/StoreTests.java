package com.example.store;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import org.junit.jupiter.api.Test;

@SpringBootTest(classes = {TestStoreApplication.class, ContainersConfig.class},
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class StoreTests {

    @LocalServerPort
    protected Integer port;


    @Test
    void testSpringAIChatMockTemplate()  {

    }
}
