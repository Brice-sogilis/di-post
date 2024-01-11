const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Test build
    const unit_tests = b.addTest(.{
        .root_source_file = .{ .path = "example.zig" },
        .target = target,
        .optimize = optimize,
    });

    // Test run (with zig build test)
    const run_unit_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_unit_tests.step);
}
