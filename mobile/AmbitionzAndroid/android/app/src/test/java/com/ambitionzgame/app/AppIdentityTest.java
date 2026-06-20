package com.ambitionzgame.app;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class AppIdentityTest {

    @Test
    public void buildConfigMatchesCanonicalIdentity() {
        assertEquals("com.ambitionzgame.app", BuildConfig.APPLICATION_ID);
        assertEquals("1.0.0-beta.2", BuildConfig.VERSION_NAME);
        assertEquals(2, BuildConfig.VERSION_CODE);
    }
}
