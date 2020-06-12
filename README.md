# QuTiP dispatcher prototype

This is just the base dispatcher, which currently acts on arbitrary types, and
dispatches only if it finds an exact match.  I suspect that we may restrict it
in the future so that it can only dispatch over `qutip.data.Data` subtypes,
because there are some dispatching optimisations I have in mind for choosing a
specialisation when there isn't a fully specified specialisation defined.

Here's a basic example:

```python
In [1]: import data
   ...:
   ...: @data.dispatch(inputs=('a', 'b'))
   ...: def multiply(a, b):
   ...:     """Multiply two things."""
   ...:     print("No specialisation known!")
   ...:
   ...: @multiply.register((int, int))
   ...: def multiply_ints(a, b):
   ...:     return int(a) * int(b)
   ...:
   ...: @multiply.register((str, str))
   ...: def multiply_strs(a, b):
   ...:     return " ".join([a, b])
   ...:

In [2]: %timeit multiply(2, 3)
803 ns ± 4.01 ns per loop (mean ± std. dev. of 7 runs, 1000000 loops each)

In [3]: %timeit multiply_ints(2, 3)
328 ns ± 26.1 ns per loop (mean ± std. dev. of 7 runs, 1000000 loops each)
```

You can see the dispatch time for two positional arguments is about 500ns,
which is pretty fast considering that it's comparable to the time of one of the
simplest possible Python functions - as soon as our dispatcher functions are
doing more work, the dispatch time will hopefully be negligible.

## Building

Standard `setuptools` build process:

```
python setup.py build_ext -i
```

## Current limitations

Currently this operates on Python objects.  I'm not certain that Cython is
expressive enough to allow dynamic casts off RTTI, but it's possible we might
not need full arbitrary dispatch anyway - it may well be a case of premature
optimisation.  Cython can't produce templated classes, but it can wrap them -
if we absolutely need it, we may be able to produce a specialised C-type
dispatcher in fully templated C++ and import it, but that's an awful lot of
work for something that might not be necessary.

The current implementation doesn't dispatch over the output types, but I know
how to write that, I've just not done it yet.

A specialisation is done for a specific type.  Subclasses of the same type will
not match this specialisation.  I would have to change the underlying data
structure holding the dispatch table to allow this, but it _is_ doable if
necessary - we would swap from dictionary lookups to probably a tree structure
which we would traverse in Cython.  In the naïve method off the top of my head,
the lookup complexity would increase from `O(d)` to `O(n*d)` for `d` dispatch
parameters and `n` possible values, but I suspect the constant factors would be
significantly better, and there may well be a path back down to `O(d)` if we
make `Data` a metaclass and insert some RTTI of our own design into all derived
classes.


## How it works

`data.dispatch` is a decorator which captures the generic function and the
keyword arguments, and passes them in to the extension type `Dispatcher` (which
we don't expose as part of the standard API because it's not necessary).

`Dispatcher` maintains the `__call__` method so that it acts as the function it
decorates, but performs multiple dispatch on the arguments.  The multiple
dispatch is done by dictionary access using a tuple of the dispatch parameters'
`__class__` objects as the lookup values to return a Python callable object
which has previously been registered with `Dispatcher.register`.

To ensure we dispatch on the correct arguments, we have to parse the function
call grammar and bind all passed arguments to the correct place.  This is
necessary to support calls to `def f(a, b): return a + 2*b` as `f(b=2, a=1)`,
_i.e._ ones where the original intent of keyword and positional arguments is
mixed, and the parameters are out-of-order.

There is a pure-Python implementation of the binding in
`inspect.Signature.bind`, but I found this took on the order of 10µs to bind
and dispatch even for really simple calls, which is unacceptably slow, so
`Dispatcher` implements its own version in Cython using the helper class
`_Binder`.  On instantiation, `_Binder` constructs default lists and dicts of
the `args` and `kwargs` parameters that it will output (for now we do not
permit `*args` or `**kwargs` forms, but `**kwargs` in particular will not be
difficult to add, and `*args` will just impose a speed penalty), and builds up
some internal data structures to allow fast location and indexing of the
dispatch inputs.

The binding is actually handled by `_Binder.bind`, which runs though all the
arguments it knows about from initialisation and fills them in.  Keyword
arguments are converted to positional ones if possible, because we get faster
indexing and unpacking on these types.  `_Binder.bind` also handles capturing
the dispatcher inputs, since its data structures allow it fast lookup of them.
