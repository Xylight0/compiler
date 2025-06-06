(module
 (import "env" "memory" (memory 1600))
 (import "env" "print" (func $print (param i32 i32)))
 (import "env" "print_err" (func $print_err (param i32 i32)))
 (import "env" "print_i32" (func $print_i32 (param i32)))
 (import "env" "print_bool" (func $print_bool (param i32)))
 (import "env" "print_i64" (func $print_i64 (param i64)))
 (import "env" "input_i32" (func $input_i32 (param) (result i32)))
 (import "env" "input_i64" (func $input_i64 (param) (result i64)))
 (export "main" (func $main))
 (table funcref (elem))
 (func
  $main
  (local $i i64)
  (local $@tmp_i32 i32)
  (local $@tmp_i64 i64)
  (i64.const 5)
  (local.set $i)
  (local.get $i)
  (i64.const 6)
  i64.lt_s
  if (i64.const 10) (local.set $i) else (i64.const 15) (local.set $i) end
  (local.get $i)
  (call $print_i64)))