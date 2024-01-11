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
