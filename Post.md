# 3 Dependency injection benefits, illustrated with Zig memory allocation case study (and other buzzwords in a long title)

## Context

While looking at [Zig](https://ziglang.org/) I found the memory allocation idioms encouraged by the language illustrative of the Dependency Injection pattern advantages. I tried to write some examples, and ended up writing more of non-zig examples

I hope the document remains consistent and usefull !

## Terminology

### Dependency Injection

- In this document, we **do** use the terms Dependency injection for what is also called the Inversion of Control pattern, or the Strategy Pattern. It designates the design principle of passing behaviour implementations or resources to a system components instead of letting each component implement their own, to leave each component responsible only of its specific domain, and to centralize transversal resources management.
- We **do not** use the term Dependency injection to designate the dependencies injection frameworks such as Spring or Guice, whose role is to ease the ‘mechanical’ part of actually applying this pattern in a codebase, for example by automating some parameter injection with annotations.

### Memory allocation

In some languages, memory management is automated, either by a [garbage collector](https://en.wikipedia.org/wiki/Garbage_collection_(computer_science))(Java, C#, Javascript, OCaml…) or by cleanup code generated during compilation (C++ [destructors](https://www.geeksforgeeks.org/destructors-c/), [Rust](https://www.rust-lang.org/) …). In others, especially [C](https://en.wikipedia.org/wiki/C_dynamic_memory_allocation), allocating and freeing memory is the responsibility of the programmers. Dynamically created (i.e. not at compile-time) objects and data structures need to be manually released in the code, requiring some ownership conventions to avoid memory leaks or conflicts.

## Benefits of dependency injection

We will focus on three main ‘features’ of dependency injection :

+ Critical resource control

+ Modularity => Testability

+ Capacity & requirements tracking

## 1) Critical resource control

### The concept

Without dependency injection, each component is responsible to allocate it’s own resources at will. These can be threads, memory, shared files, a database connection… With time and complexification of the system, the number and the degree of nesting of these components and sub-modules is likely to grow, and this "help yourself" behaviour can lead to conflicts or starvation in other parts of the system. Consider the following Java code allocating threads to parallelize some computations:

```java source=java/Example.java lines=6-22
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
```

This works fine when you instanciate only one `Compute` instance at the root of the application, but it could quickly become a source of overhead if many instances were to be used, even more if, for example, each thread allocates a lot of memory which cannot be garbage collected until the computation is done. Plus, we had not to forget to shutdown the threadpool after the computation. In this “help yourself” approach, managing resources allocation, would have to be done by each classes requiring the resource, mixing their real responsibility with such housekeeping, error prone tasks.

Switching to this :

```java source=java/Example.java lines=24-35
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
```

Now creating the threadPool is the responsibility of the caller, who can limit the number of threads allocated. In addition, we do not have to worry about shutting down the pool, this task can be centralized limiting the risk of errors.

*Sidenote : many other options are available for concurrency and parallelism control in the JVM, such as* *[Java21 virtual threads and structured concurrency mechanisms](https://docs.oracle.com/en/java/javase/21/core/structured-concurrency.html#GUID-AA992944-AABA-4CBC-8039-DE5E17DE86DB)* *or* *[Kotlin coroutines](https://kotlinlang.org/docs/coroutines-overview.html)*.

### Zig example

In C, allocating memory can be done from anywhere, using `malloc`. A ‘greedy’ function could allocate more memory than suitable, leaving each function responsible to allocate the right amount of memory, and to handle allocation failure. For example, an implementation of the caesar cipher could be done like this :

```c source=c/example.c lines=5-14
const  char * caesarCiphered(unsigned char offset, const  char * clearText, unsigned  int textLength) {
	char * result = malloc(textLength); // Caller choose the right amount of memory to allocate
	// char * result = malloc(textLength * 3); Nothing would stop us if we tried to allocate more than necessary

	for(unsigned  int i = 0; i< textLength; i++) {
		result[i] = clearText[i] + offset;
	}

	return result;
}
```

In case of an allocation error, e rely on the function to adopt an appropriate behaviour to crash or recover.

In Zig the idiom is to inject the allocator:

```zig source=zig/example.zig lines=3-13
fn caesarCiphered(allocator: std.mem.Allocator, offset: u8, clearText: []const u8) ![]const u8 {
    const result = try allocator.alloc(u8, clearText.len); // **try** transfer the potential error thrown by allocate(), ence the '!' in the function return type

    // const result = try allocator.allocate(u8, clearText.len * 3); // Here the actual implementation of allocator could limit raise an error if we tried to allocate more bytes than nnecessary

    for (0..clearText.len) |i| {
        result[i] = clearText[i] +% offset; // +% performs modular arithmetic to wrap in 0-255 range
    }

    return result;
}
```

As the caller is now controlling the allocation, it can raise an error if the function is trying to allocate more memory than expected. In case of an allocation error, the caller control the error raised by the allocator and the potential recovery strategies to apply, freeing the function from this responsibility.

## 2) Modularity => Testability

Another benefit of dependency injection is that it eases the unit testing of a component. Consider the following NodeJS function where we want to dispatch a message to different address according to the message content:

```ts source=node/example.ts lines=1-9
import axios from "axios";

async function relayMessageToRelevantPeople(message: string) {
  if (message.match("CONFIDENTIAL")) {
    await axios.post("http://vip/mailbox", { message: message });
  } else {
    await axios.post("http://everyone/mailbox", { message: message });
  }
}
```

The choice of the messaging protocol (http) and the knowledge of the addresses have to be decided or known by the function. This bring some complications, among which :

- If we want to switch to another message relay mechanism, such as an event bus protocol, we would have to update all the functions adopting the same model as `relayMessageToRelevantPeople`
- In the same style, if we want to reuse the same logic of message discrimination with another framework or protocol, we would have to duplicate the function.
- To be able to test the behaviour we actually care about (redirecting the message based on its content), the test setup becomes quite involved:

```ts source=node/example.ts lines=30-47
import nock from "nock"; // Http & DNS mocking framework
axios.defaults.adapter = "http"; // Allows nock to intercept axios requests

describe("relayMessageToRelevantPeople", function () {
  it("redirect confidential messages only to vip(s)", async function () {
    const scope = nock("http://vip") // intercepts request to this hostname
      .post("/mailbox") // expect a post request to /mailbox
      .reply(200, "OK"); // reply with OK when requested
    await relayMessageToRelevantPeople("this is CONFIDENTIAL");
    scope.done(); // Will fail if the expected request was not received
  });

  it("redirect other messages to everyone", async function () {
    const scope = nock("http://everyone").post("/mailbox").reply(200, "OK");
    await relayMessageToRelevantPeople("this is CONFITURE");
    scope.done();
  });
});
```

*Sidenote : nock can actually be a pretty usefull tool* (*[documentation here](https://www.npmjs.com/package/nock#axios)*)

We have to setup an entire http interception mechanism, and even a pretty simple test becomes noisy because of the surrounding network mechanics.

We could have abstracted and injected the vip and everyone communication channels:

```ts source=node/example.ts lines=11-26
interface Channel {
  // type of an async function accepting a string and returning void
  (message: string): Promise<void>;
}

async function relayMessageToRelevantChannel(
  message: string,
  channels: {Channel, Channel],
) {
  const [sendVip, sendEveryone] = channels; // destructure channels
  if (message.match("CONFIDENTIAL")) {
    await sendVip(message);
  } else {
    await sendEveryone(message);
  }
}
```

the test does not require the http setup anymore :

```ts source=node/example.ts lines=49-77
describe("relayMessageToRelevantPeople with channel injection", function () {
  it("redirect confidential messages only to vip(s)", async function () {
    // Setup our mocks without needing http
    let vipCalled = false; // A flag indicating that the vip channel mock has been called
    const vipChannel = async (_: string) => {
      vipCalled = true;
    }; // A mock only updating our flag when called
    const everyoneChannel = async (_: string) => {}; // A mock doiing nothing

    await relayMessageToRelevantChannel("this is CONFIDENTIAL", [
      vipChannel,
      everyoneChannel,
    ]);
    assert.equal(vipCalled, true);
  });

  it("redirect other messages to everyone", async function () {
    let everyoneCalled = false;
    const everyoneChannel = async (msg: string) => {
      everyoneCalled = true;
    };
    const vipChannel = async (msg: string) => {};
    await relayMessageToRelevantChannel("this is CONFITURE", [
      vipChannel,
      everyoneChannel,
    ]);
    assert.equal(everyoneCalled, true);
  });
});
```

### Zig example

Memory leaks prevention and detection motivated the development of many Memory Analysis tools such as AddressSanitizer or Valgrind. These external tools represent an additional effort when integrating into the CI process, especially when you want to scan many individual components, an are external to the language, requiring expertise. Despite not being enough to catch all kinds of memory leaks, Zig **builtin** `std.testing.allocator`takes advantage of the dependency injection to catch a whole range of memory leaks bugs whith minimal overhead when writing your tests:

```zig source=zig/example.zig lines=26-46
test "This would pass" {
    var list = std.ArrayList(i32).init(std.testing.allocator); // here we inject the testing allocator, which will track all memory allocations performed by list
    defer list.deinit(); // ensure list memory will be freed at the end of the scope
    try list.append(42);
    try std.testing.expect(list.items[0] == 42);
}

test "Detecting a memory leak" {
    var list = std.ArrayList(i32).init(std.testing.allocator);
    try list.append(42);
    try std.testing.expect(list.items[0] == 42);

    // list was not freed !
    std.debug.print("Expected memory leaks logs here, keeep calm ===> \n", .{});
    const detectLeak = std.testing.allocator_instance.detectLeaks();
    std.debug.print("\n<=== End of expected memory leaks logs", .{});
    try std.testing.expect(detectLeak == true);

    // if we do not actually free the list, the test would fail, helping us detecting memory leaks at test time without additionnal tools
    list.deinit();
}
```

## 3) Capacity & requirements tracking

This point is simple but underrated: when ensuring that every resource or external behaviour is injected instead of creating them at will, the signature of the functions/methods/classes/… reveals their needs, and possibly some design flows :

```python
# Making http in the middle of an arithmetic operation ? Never!
def add(a: int, b: int, server: HttpServer) -> int:
	...
```

```kotlin
// Writing debug files in the middle of a geometric operation ? ... Never ?
fun splitPolygonInSegments(polygon: Polygon, debugDir: Path?): List<Segment> {
	// ...    
	plotSegment(s, debugDir / "segment_image.png")
	// ...
}
```

### Zig example

Allocating memory can sometime be avoided. When forced to explicitly pass allocators when needed, you are more likely to think about a more efficient or simple solution :

```zig source=zig/example.zig lines=48-72
fn sumOddNumbers(numbers: []const u32) u32 {
    var res: u32 = 0;
    for (numbers) |n| {
        if (n % 2 == 1) res += n;
    }
    return res;
}

fn sumOddNumbersInTwoPhases(allocator: std.mem.Allocator, numbers: []const u32) !u32 {
    var oddNumbers = std.ArrayList(u32).init(allocator);
    defer oddNumbers.deinit();

    // First select odd numbers
    for (numbers) |n| {
        if (n % 2 == 1) try oddNumbers.append(n);
    }

    // Then sum them
    var res: u32 = 0;
    for (oddNumbers.items) |n| {
        res += n;
    }

    return res;
}
```