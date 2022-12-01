package example;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.junit.function.ThrowingRunnable;

public class DummyClassTest {
    DummyClass dummyClass;

    @Before
    public void setUp() throws Exception {
        dummyClass = new DummyClass();
    }

    @Test
    public void parseStringToInt_str() {
        Assert.assertThrows("Received null integer!", IllegalArgumentException.class, new ThrowingRunnable() {
            @Override
            public void run() throws Throwable {
                dummyClass.parseStringToInt("sfdg");
            }
        });
    }

    @Test
    public void parseStringToInt_int() {
        Assert.assertEquals(1, dummyClass.parseStringToInt("1"));
    }

    @Test
    public void parseStringToInt_float() {
        Assert.assertThrows("For input string: \"1.0\"", NumberFormatException.class, new ThrowingRunnable() {
            @Override
            public void run() throws Throwable {
                dummyClass.parseStringToInt("1.0");
            }
        });
    }


    @Test
    public void addCalc() {
        Assert.assertEquals(5, dummyClass.addCalc(1, 4));
    }


}