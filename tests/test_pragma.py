from unittest import TestCase
from miniutils import pragma
from textwrap import dedent
import inspect


class PragmaTest(TestCase):
    def setUp(self):
        pass
        # # This is a quick hack to disable contracts for testing if needed
        # import contracts
        # contracts.enable_all()


class TestUnroll(PragmaTest):
    def test_unroll_range(self):
        @pragma.unroll
        def f():
            for i in range(3):
                yield i

        self.assertEqual(list(f()), [0, 1, 2])

    def test_unroll_various(self):
        g = lambda: None
        g.a = [1, 2, 3]
        g.b = 6

        @pragma.unroll(return_source=True)
        def f(x):
            y = 5
            a = range(3)
            b = [1, 2, 4]
            c = (1, 2, 5)
            d = reversed(a)
            e = [x, x, x]
            f = [y, y, y]
            for i in a:
                yield i
            for i in b:
                yield i
            for i in c:
                yield i
            for i in d:
                yield i
            for i in e:
                yield i
            for i in f:
                yield i
            for i in g.a:
                yield i
            for i in [g.b + 0, g.b + 1, g.b + 2]:
                yield i

        result = dedent('''
        def f(x):
            y = 5
            a = range(3)
            b = [1, 2, 4]
            c = 1, 2, 5
            d = reversed(a)
            e = [x, x, x]
            f = [y, y, y]
            yield 0
            yield 1
            yield 2
            yield 1
            yield 2
            yield 4
            yield 1
            yield 2
            yield 5
            for i in d:
                yield i
            yield x
            yield x
            yield x
            yield 5
            yield 5
            yield 5
            yield 1
            yield 2
            yield 3
            yield 6
            yield 7
            yield 8
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_unroll_const_list(self):
        @pragma.unroll
        def f():
            for i in [1, 2, 4]:
                yield i

        self.assertEqual(list(f()), [1, 2, 4])

    def test_unroll_const_tuple(self):
        @pragma.unroll
        def f():
            for i in (1, 2, 4):
                yield i

        self.assertEqual(list(f()), [1, 2, 4])

    def test_unroll_range_source(self):
        @pragma.unroll(return_source=True)
        def f():
            for i in range(3):
                yield i

        result = dedent('''
        def f():
            yield 0
            yield 1
            yield 2
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_unroll_list_source(self):
        @pragma.unroll(return_source=True)
        def f():
            for i in [1, 2, 4]:
                yield i

        result = dedent('''
        def f():
            yield 1
            yield 2
            yield 4
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_unroll_dyn_list_source(self):
        @pragma.unroll(return_source=True)
        def f():
            x = 3
            a = [x, x, x]
            for i in a:
                yield i
            x = 4
            a = [x, x, x]
            for i in a:
                yield i

        result = dedent('''
        def f():
            x = 3
            a = [x, x, x]
            yield 3
            yield 3
            yield 3
            x = 4
            a = [x, x, x]
            yield 4
            yield 4
            yield 4
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_unroll_dyn_list(self):
        def summation(x=0):
            a = [x, x, x]
            v = 0
            for _a in a:
                v += _a
            return v

        summation_source = pragma.unroll(return_source=True)(summation)
        summation = pragma.unroll(summation)

        code = dedent('''
        def summation(x=0):
            a = [x, x, x]
            v = 0
            v += x
            v += x
            v += x
            return v
        ''')
        self.assertEqual(summation_source.strip(), code.strip())
        self.assertEqual(summation(), 0)
        self.assertEqual(summation(1), 3)
        self.assertEqual(summation(5), 15)

    def test_unroll_2range_source(self):
        @pragma.unroll(return_source=True)
        def f():
            for i in range(3):
                for j in range(3):
                    yield i + j

        result = dedent('''
        def f():
            yield 0 + 0
            yield 0 + 1
            yield 0 + 2
            yield 1 + 0
            yield 1 + 1
            yield 1 + 2
            yield 2 + 0
            yield 2 + 1
            yield 2 + 2
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_unroll_2list_source(self):
        @pragma.unroll(return_source=True)
        def f():
            for i in [[1, 2, 3], [4, 5], [6]]:
                for j in i:
                    yield j

        result = dedent('''
        def f():
            yield 1
            yield 2
            yield 3
            yield 4
            yield 5
            yield 6
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_external_definition(self):
        # Known bug: this works when defined as a kwarg, but not as an external variable, but ONLY in unittests...
        # External variables work in practice
        @pragma.unroll(return_source=True, a=range)
        def f():
            for i in a(3):
                print(i)

        result = dedent('''
        def f():
            print(0)
            print(1)
            print(2)
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_tuple_assign(self):
        # This is still early code, so just make sure that it recognizes when a name is assigned to... we don't get values yet
        # TODO: Implement tuple assignment
        @pragma.unroll(return_source=True)
        def f():
            x = 3
            ((y, x), z) = ((1, 2), 3)
            for i in [x,x,x]:
                print(i)

        result = dedent('''
        def f():
            x = 3
            (y, x), z = (1, 2), 3
            print(x)
            print(x)
            print(x)
        ''')
        self.assertEqual(f.strip(), result.strip())


class TestCollapseLiterals(PragmaTest):
    def test_full_run(self):
        def f(y):
            x = 3
            r = 1 + x
            for z in range(2):
                r *= 1 + 2 * 3
                for abc in range(x):
                    for a in range(abc):
                        for b in range(y):
                            r += 1 + 2 + y
            return r

        import inspect
        deco_f = pragma.collapse_literals(f)
        self.assertEqual(f(0), deco_f(0))
        self.assertEqual(f(1), deco_f(1))
        self.assertEqual(f(5), deco_f(5))
        self.assertEqual(f(-1), deco_f(-1))

        deco_f = pragma.collapse_literals(pragma.unroll(f))
        self.assertEqual(f(0), deco_f(0))
        self.assertEqual(f(1), deco_f(1))
        self.assertEqual(f(5), deco_f(5))
        self.assertEqual(f(-1), deco_f(-1))

    def test_basic(self):
        @pragma.collapse_literals(return_source=True)
        def f():
            return 1 + 1

        result = dedent('''
        def f():
            return 2
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_vars(self):
        @pragma.collapse_literals(return_source=True)
        def f():
            x = 3
            y = 2
            return x + y

        result = dedent('''
        def f():
            x = 3
            y = 2
            return 5
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_partial(self):
        @pragma.collapse_literals(return_source=True)
        def f(y):
            x = 3
            return x + 2 + y

        result = dedent('''
        def f(y):
            x = 3
            return 5 + y
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_constant_index(self):
        @pragma.collapse_literals(return_source=True)
        def f():
            x = [1,2,3]
            return x[0]

        result = dedent('''
        def f():
            x = [1, 2, 3]
            return 1
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_with_unroll(self):
        @pragma.collapse_literals(return_source=True)
        @pragma.unroll
        def f():
            for i in range(3):
                print(i + 2)

        result = dedent('''
        def f():
            print(2)
            print(3)
            print(4)
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_with_objects(self):
        @pragma.collapse_literals(return_source=True)
        def f():
            v = [object(), object()]
            return v[0]

        result = dedent('''
        def f():
            v = [object(), object()]
            return v[0]
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_invalid_collapse(self):
        import warnings
        warnings.resetwarnings()
        with warnings.catch_warnings(record=True) as w:
            @pragma.collapse_literals
            def f():
                return 1 + "2"

            self.assertTrue(issubclass(w[-1].category, UserWarning))

    # TODO: implement the features to get this test to work
    # def test_conditional_erasure(self):
    #     @pragma.collapse_literals(return_source=True)
    #     def f(y):
    #         x = 0
    #         if y == x:
    #             x = 1
    #         return x
    #
    #     result = dedent('''
    #     def f(y):
    #         x = 0
    #         if y == 0:
    #             x = 1
    #         return x
    #     ''')
    #     self.assertEqual(f.strip(), result.strip())

    def test_constant_conditional_erasure(self):
        @pragma.collapse_literals(return_source=True)
        def f(y):
            x = 0
            if x <= 0:
                x = 1
            return x

        result = dedent('''
        def f(y):
            x = 0
            x = 1
            return 1
        ''')
        self.assertEqual(f.strip(), result.strip())

        def fn():
            if x == 0:
                x = 'a'
            elif x == 1:
                x = 'b'
            else:
                x = 'c'
            return x

        result0 = dedent('''
        def fn():
            x = 'a'
            return 'a'
        ''')
        result1 = dedent('''
        def fn():
            x = 'b'
            return 'b'
        ''')
        result2 = dedent('''
        def fn():
            x = 'c'
            return 'c'
        ''')
        self.assertEqual(pragma.collapse_literals(return_source=True, x=0)(fn).strip(), result0.strip())
        self.assertEqual(pragma.collapse_literals(return_source=True, x=1)(fn).strip(), result1.strip())
        self.assertEqual(pragma.collapse_literals(return_source=True, x=2)(fn).strip(), result2.strip())


class TestDeindex(PragmaTest):
    def test_with_literals(self):
        v = [1, 2, 3]
        @pragma.collapse_literals(return_source=True)
        @pragma.deindex(v, 'v')
        def f():
            return v[0] + v[1] + v[2]

        result = dedent('''
        def f():
            return 6
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_with_objects(self):
        v = [object(), object(), object()]
        @pragma.deindex(v, 'v', return_source=True)
        def f():
            return v[0] + v[1] + v[2]

        result = dedent('''
        def f():
            return v_0 + v_1 + v_2
        ''')
        self.assertEqual(result.strip(), f.strip())

    def test_with_unroll(self):
        v = [None, None, None]

        @pragma.deindex(v, 'v', return_source=True)
        @pragma.unroll(lv=len(v))
        def f():
            for i in range(lv):
                yield v[i]

        result = dedent('''
        def f():
            yield v_0
            yield v_1
            yield v_2
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_with_literals_run(self):
        v = [1, 2, 3]
        @pragma.collapse_literals
        @pragma.deindex(v, 'v')
        def f():
            return v[0] + v[1] + v[2]

        self.assertEqual(f(), sum(v))

    def test_with_objects_run(self):
        v = [object(), object(), object()]
        @pragma.deindex(v, 'v')
        def f():
            return v[0]

        self.assertEqual(f(), v[0])

    def test_with_variable_indices(self):
        v = [object(), object(), object()]
        @pragma.deindex(v, 'v', return_source=True)
        def f(x):
            yield v[0]
            yield v[x]

        result = dedent('''
        def f(x):
            yield v_0
            yield v[x]
        ''')
        self.assertEqual(f.strip(), result.strip())

    def test_dynamic_function_calls(self):
        funcs = [lambda x: x, lambda x: x ** 2, lambda x: x ** 3]

        # TODO: Support enumerate transparently
        # TODO: Support tuple assignment in loop transparently

        @pragma.deindex(funcs, 'funcs')
        @pragma.unroll(lf=len(funcs))
        def run_func(i, x):
            for j in range(lf):
                if i == j:
                    return funcs[j](x)

        self.assertEqual(run_func(0, 5), 5)
        self.assertEqual(run_func(1, 5), 25)
        self.assertEqual(run_func(2, 5), 125)

        result = dedent('''
        def run_func(i, x):
            if i == 0:
                return funcs_0(x)
            if i == 1:
                return funcs_1(x)
            if i == 2:
                return funcs_2(x)
        ''')
        self.assertEqual(inspect.getsource(run_func).strip(), result.strip())


class TestDictStack(PragmaTest):
    def test_most(self):
        stack = pragma.DictStack()
        stack.push({'x': 3})
        stack.push()
        stack['x'] = 4
        self.assertEqual(stack['x'], 4)
        res = stack.pop()
        self.assertEqual(res['x'], 4)
        self.assertEqual(stack['x'], 3)
        self.assertIn('x', stack)
        stack.items()
        stack.keys()
        del stack['x']
        self.assertNotIn('x', stack)
