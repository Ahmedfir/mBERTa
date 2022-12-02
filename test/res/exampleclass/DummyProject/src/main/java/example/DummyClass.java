package example;

public class DummyClass {

    public int parseStringToInt(String s) {
        if (s != null) {
            return Integer.valueOf(s);
        } else {
            throw new IllegalArgumentException("Received null integer!");
        }
    }

    public int addCalc(int int1, int int2) {
        if (int1 == int2){
            return 2 * int1;
        } else{
            return int1 + int2;
        }
    }

    public static void main(String... args) {
        DummyClass dummyClass = new DummyClass();
        int a = dummyClass.parseStringToInt(args[0]);
        int b = dummyClass.parseStringToInt(args[1]);
        System.out.println(args[0] + " + " + args[1] + " = " + dummyClass.addCalc(a, b));
    }
}
