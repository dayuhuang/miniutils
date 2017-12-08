import ast
import inspect

from .core import TrackedContextTransformer, function_ast, constant_dict, make_function_transformer, \
    resolve_name_or_attribute, resolve_literal
from .. import magic_contract
from collections import OrderedDict as odict


# stmt = FunctionDef(identifier name, arguments args,
#                        stmt* body, expr* decorator_list, expr? returns)
#           | AsyncFunctionDef(identifier name, arguments args,
#                              stmt* body, expr* decorator_list, expr? returns)
#
#           | ClassDef(identifier name,
#              expr* bases,
#              keyword* keywords,
#              stmt* body,
#              expr* decorator_list)
#           | Return(expr? value)
#
#           | Delete(expr* targets)
#           | Assign(expr* targets, expr value)
#           | AugAssign(expr target, operator op, expr value)
#           -- 'simple' indicates that we annotate simple name without parens
#           | AnnAssign(expr target, expr annotation, expr? value, int simple)
#
#           -- use 'orelse' because else is a keyword in target languages
#           | For(expr target, expr iter, stmt* body, stmt* orelse)
#           | AsyncFor(expr target, expr iter, stmt* body, stmt* orelse)
#           | While(expr test, stmt* body, stmt* orelse)
#           | If(expr test, stmt* body, stmt* orelse)
#           | With(withitem* items, stmt* body)
#           | AsyncWith(withitem* items, stmt* body)
#
#           | Raise(expr? exc, expr? cause)
#           | Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
#           | Assert(expr test, expr? msg)
#
#           | Import(alias* names)
#           | ImportFrom(identifier? module, alias* names, int? level)
#
#           | Global(identifier* names)
#           | Nonlocal(identifier* names)
#           | Expr(expr value)
#           | Pass | Break | Continue
#
#           -- XXX Jython will be different
#           -- col_offset is the byte offset in the utf8 string the parser uses
#           attributes (int lineno, int col_offset)


class _InlineBodyTransformer(ast.NodeTransformer):
    def __init__(self, func_name, param_names):
        self.func_name = func_name
        self.param_names = param_names

    def visit_Name(self, node):
        if node.id in self.param_names:
            return ast.Subscript(value=ast.Name(id=self.func_name),
                                 slice=ast.Index(ast.Name(node.id)),
                                 expr_context=getattr(node, 'expr_context', ast.Load()))

    def visit_Return(self, node):
        result = []
        if node.value:
            result.append(ast.Assign(targets=[ast.Subscript(value=ast.Name(id=self.func_name),
                                                            slice=ast.Name(id='return'),
                                                            expr_context=ast.Store())],
                                     value=node.value))
        result.append(ast.Break())
        return result


class InlineTransformer(TrackedContextTransformer):
    def __init__(self, *args, funs=None, **kwargs):
        assert funs is not None
        super().__init__(*args, **kwargs)

        self.funs = funs
        self.code_blocks = []


    def nested_visit(self, nodes):
        """When we visit a block of statements, create a new "code block" and push statements into it"""
        lst = []
        self.code_blocks.append(lst)
        print(nodes)
        for n in nodes:
            res = self.visit(n)
            if res is None:
                continue
            elif isinstance(res, list):
                lst += res
            else:
                lst.append(res)
        self.code_blocks.pop()
        return lst

    def visit_Call(self, node):
        """When we see a function call, insert the function body into the current code block, then replace the call
        with the return expression """
        node_fun = resolve_name_or_attribute(resolve_literal(node.func, self.ctxt), self.ctxt)

        for (fun, fname, fsig, fbody) in self.funs:
            if fun != node_fun:
                continue

            cur_block = self.code_blocks[-1]

            # Load arguments into their appropriate variables
            args = node.args
            keywords = [(name.id, value) for name, value in node.keywords if name is not None]
            kw_dict = [value for name, value in node.keywords if name is None]
            kw_dict = constant_dict(kw_dict, self.ctxt) or {}
            keywords += list(kw_dict.items())
            bound_args = fsig.bind(*node.args, **odict(keywords))
            bound_args.apply_defaults()

            # Create args dictionary
            # fun_name = {}
            cur_block.append(ast.Assign(targets=[ast.Name(id=fname)],
                                        value=ast.Dict(keys=[], values=[])))

            for arg_name, arg_value in bound_args.arguments.items():
                # fun_name['param_name'] = param_value
                cur_block.append(ast.Assign(targets=[ast.Subscript(value=ast.Name(id=fname),
                                                                   slice=ast.Str(arg_name),
                                                                   expr_context=ast.Store())],
                                            value=arg_value))

            # Inline function code
            cur_block.append(ast.For(target=ast.Name(id='____'),
                                     iter=ast.Call(func=ast.Name(id='range'),
                                                   args=[ast.Num(1)],
                                                   keywords=[]),
                                     body=fbody,
                                     orelse=[]))

            # fun_name['return']
            return ast.Subscript(value=ast.Name(id=fname),
                                 slice=ast.Str('return'),
                                 expr_context=ast.Load())

        else:
            return node



    ###################################################
    # From here on down, we just have handlers for ever AST node that has a "code block" (stmt*)
    ###################################################

    def visit_FunctionDef(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)

    def visit_For(self, node):
        node.body = self.nested_visit(node.body)
        node.orelse = self.nested_visit(node.orelse)
        return self.generic_visit(node)

    def visit_AsyncFor(self, node):
        node.body = self.nested_visit(node.body)
        node.orelse = self.nested_visit(node.orelse)
        return self.generic_visit(node)

    def visit_While(self, node):
        node.body = self.nested_visit(node.body)
        node.orelse = self.nested_visit(node.orelse)
        return self.generic_visit(node)

    def visit_If(self, node):
        node.body = self.nested_visit(node.body)
        node.orelse = self.nested_visit(node.orelse)
        return self.generic_visit(node)

    def visit_With(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)

    def visit_AsyncWith(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)

    def visit_Try(self, node):
        node.body = self.nested_visit(node.body)
        node.body = self.nested_visit(node.orelse)
        node.body = self.nested_visit(node.finalbody)
        return self.generic_visit(node)

    def visit_Module(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        node.body = self.nested_visit(node.body)
        return self.generic_visit(node)


# Inline functions?
# You could do something like:
# args, kwargs = (args_in), (kwargs_in)
# function_body
# result = return_expr
@magic_contract
def inline(*funs_to_inline, **kwargs):
    """
    :param funs_to_inline: The inner called function that should be inlined in the wrapped function
    :type funs_to_inline: tuple(function)
    :return: The unrolled function, or its source code if requested
    :rtype: function
    """
    funs = []
    for fun_to_inline in funs_to_inline:
        fname = fun_to_inline.__name__
        fsig = inspect.signature(fun_to_inline)
        _, fbody, _ = function_ast(fun_to_inline)

        new_name = '_{fname}_{name}'

        import astor
        print(astor.dump_tree(fbody))
        name_transformer = _InlineBodyTransformer(fname, new_name)
        fbody = [name_transformer.visit(stmt) for stmt in fbody]
        fbody = [stmt for visited in fbody for stmt in (visited if isinstance(visited, list) else [visited])]
        print(astor.dump_tree(fbody))
        funs.append((fun_to_inline, fname, fsig, fbody))

    return make_function_transformer(InlineTransformer,
                                     'inline',
                                     'Inline the specified function within the decorated function',
                                     funs=funs)(**kwargs)
