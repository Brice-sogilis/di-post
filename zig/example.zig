const std = @import("std");

fn caesarCiphered(allocator: std.mem.Allocator, offset: u8, clearText: []const u8) ![]const u8 {
    const result = try allocator.alloc(u8, clearText.len); // **try** transfer the potential error thrown by allocate(), ence the '!' in the function return type

    // const result = try allocator.allocate(u8, clearText.len * 3); // Here the actual implementation of allocator could limit raise an error if we tried to allocate more bytes than nnecessary

    for (0..clearText.len) |i| {
        result[i] = clearText[i] +% offset; // +% performs modular arithmetic to wrap in 0-255 range
    }

    return result;
}

test "caesarCiphered" {
    const clearText = "Xtlnqnx%wthpx&";
    var ciphered = try caesarCiphered(std.testing.allocator, 251, clearText);

    // We know how to deal with the returned memory since we know the allocator we passed
    // Note: the testing allocator would fail the test if we forget this call, helping us catch memory leak errors at test time
    defer std.testing.allocator.free(ciphered);

    try std.testing.expectEqualStrings("Sogilis rocks!", ciphered);
}

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
