import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ForkJoinPool;

public class Example {
    class Compute {
        public int run() throws ExecutionException, InterruptedException {
            // Allocate 10 threads
            final var threadPool = new ForkJoinPool(10);
            try {
                return threadPool.submit(() ->
                    List.of(1,2,3,4,5,6,7,8,9,10)
                    .parallelStream() // Run the subsequent map in parallel
                    .map(n -> n * 2) // Multiply by 2 each value
                    .reduce(0, (a,b) -> a + b)) // Sum each result=)
                    .get();

            } finally {
                threadPool.shutdown();
            }
        }
    }

    class ComputeWithInjectedResource {
        // threadPool is now passed by the caller of the computation
        public int run(ForkJoinPool threadPool) throws ExecutionException, InterruptedException {
              return threadPool.submit(() ->
                    List.of(1,2,3,4,5,6,7,8,9,10)
                      .parallelStream() // Run the subsequent map in parallel
                      .map(n -> n * 2) // Multiply by 2 each value
                      .reduce(0, (a,b) -> a + b)) // Sum each result
                      .get(); // Collect
            
        }
    }

    void tests() throws Exception {
        var r1 = new Compute().run();
        assert r1 == 110;

        var r2 = new ComputeWithInjectedResource().run(new ForkJoinPool(10));
        assert r2 == 110;
    }

    public static void main(String[] _args) throws Exception {
        new Example().tests();
    }
}