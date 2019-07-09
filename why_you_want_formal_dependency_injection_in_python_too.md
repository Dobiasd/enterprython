Why you want formal dependency injection in Python too
======================================================

In other languages, e.g., Java, explicit dependency injection is part of daily business.
Python projects however very rarely make use of this technique.
I'd like to make a case for why it might be useful to rethink this approach.

Let's say you have a class implementing some business logic,
which depends on external data:

```python
# customer.py
from typing import NamedTuple

class Customer(NamedTuple):
    name: str
    value_in_dollars: int
```

```python
# domain.py
from customer import Customer

class DomainLogic:
    def get_all_customers(self):
        # Imagine some database query here.
        return [Customer('SmallCorp', 1000),
                Customer('MegaCorp', 1000000)]

    def most_valuable_customer(self):
        return max(self.get_all_customers(),
                   key=lambda customer: customer.value_in_dollars)
```

The function for retrieving the data (`get_all_customers`) might need some state,
e.g., a database connection.

Since you apply the [single-responsibility principle](https://en.wikipedia.org/wiki/Single_responsibility_principle),
you don't want to manage the connection in `DomainLogic`.
Instead, you'll use an additional [data access object](https://en.wikipedia.org/wiki/Data_access_object), encapsulating it:

```python
# database_connection.py
from typing import List

from customer import Customer

class Connection:
    def __init__(self) -> None:
        # URL, credentials etc. might be retrieved from some config here first.
        print('Connecting to database.')

    def get_all_customers(self) -> List[Customer]:
        # Imagine some database query here.
        return [Customer('SmallCorp', 1000),
                Customer('MegaCorp', 1000000)]
```

```python
# domain.py
from customer import Customer
from database_connection import Connection

class DomainLogic:
    def __init__(self) -> None:
        self.data_access = DomainLogic.init_data_access()

    @staticmethod
    def init_data_access() -> Connection:
        return Connection()

    def most_valuable_customer(self) -> Customer:
        return max(self.data_access.get_all_customers(),
                   key=lambda customer: customer.value_in_dollars)

```

Now you need to unit test the complex implementation of your business logic.
For this, you'll want to replace `data_access` with some mock.
In Python, there are multiple options to do so.
A simple and common one,
using [monkey patching](https://stackoverflow.com/questions/5626193/what-is-monkey-patching),
is to replace the `DomainLogic.init_data_access` with something
that returns a mock-data source:

```python
# test.py
import unittest
from typing import List

from customer import Customer
from database_connection import Connection
from domain import DomainLogic

class MockConnection(Connection):
    def __init__(self):
        self.customers = [Customer('SmallTestCorp', 100),
                          Customer('BigTestCorp', 200)]

    def get_all_customers(self) -> List[Customer]:
        return self.customers

def create_mock_connection() -> Connection:
    return MockConnection()

class DomainLogicTest(unittest.TestCase):
    def test_most_valuable_customer(self) -> None:
        setattr(DomainLogic, 'init_data_access', create_mock_connection)
        domain_logic = DomainLogic()
        mvc = domain_logic.most_valuable_customer()
        self.assertEqual('BigTestCorp', mvc.name)

```

This works, but it has three big disadvantages:

First, the fact that `DomainLogic` has a dependency at all
(in our case a `Connection` object) is totally hidden.
One has to look into the implementation of `DomainLogic` to actually find out about it.
Such [surprises](https://en.wikipedia.org/wiki/Principle_of_least_astonishment)
make it harder for users of your class `DomainLogic`
i.e., other developers, including your future self,
to use and test it properly.

Second, you can no longer safely use a unit-testing framework
running multiple tests concurrently, because test cases might perform
different monkey patchings on the same classes,
and thus step on each other's toes.

Third, in the case of multiple dependencies,
not all tests might need to patch the same number of things in the class.
Then, even with non-concurrent test execution,
this can end up in not correctly resetting the "state" of the class in some place
after one test, and subsequently invalidating other tests.
The overall success of the test suite
will depend on the order of execution of the test cases
if not all developers take special care. Yikes!

In general, one runs into the same problems as usual
when manually mutating (and depending on) some global state from different places.
In this case, it's just not some normal runtime value
but the class itself is mutated.

Having a globally accessible [service locator](https://en.wikipedia.org/wiki/Service_locator_pattern),
actively called from within our `DomainLogic` constructor to get the required `Connection` instance,
would also not solve the problem.
The dependencies would still depend on mutatable global state,
and be hidden instead of being visible on our classes' APIs.

So the sane approach is to use [inversion of control](https://en.wikipedia.org/wiki/Inversion_of_control)
to make the dependency explicit
by letting the constructor of `DomainLogic` take the data-access object to use
as a parameter instead of monkeying around with the class itself:

```python
# domain.py
from database_connection import Connection

class DomainLogic:
    def __init__(self, data_access: Connection):
        self.data_access = data_access

    def most_valuable_customer(self):
        return max(self.data_access.get_all_customers(),
                   key=lambda customer: customer.value_in_dollars)
```

(To adhere to the
[dependency-inversion principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle),
`__init__` could be implemented against
an [interface](https://docs.python.org/3/library/abc.html)
instead of a concrete `Connection` implementation.)

Since we now cleanly [separated the concerns](https://en.wikipedia.org/wiki/Separation_of_concerns)
of *creating* and *using* the `Connection`,
we can instantiate `DomainLogic` with whatever data source is suitable for any given situation:

```python
from database_connection import Connection
from domain import DomainLogic

if __name__ == '__main__':
    business = DomainLogic(Connection())
```

```python
class DomainLogicTest(unittest.TestCase):
    def test_most_valuable_customer(self) -> None:
        domain_logic = DomainLogic(create_mock_connection())
```

So this already solves the three pain points mentioned earlier.

---

Now it's time to make using this technique as convenient as possible.

With larger, real-world dependency trees, the shown manual injection
can become quite cumbersome,
as the following example, creating a hypothetical `Controller`, shows:

```python
some_repository = SomeRepository()
my_controller = Controller(
                    SomeService(
                        some_repository
                    ),
                    SomeOtherService(
                        some_repository,
                        SomeOtherRepository()
                    )
                )
```

Also, some things, like repositories,
might need to be a [singleton](https://en.wikipedia.org/wiki/Singleton_pattern) instance,
i.e., we only want to instantiate
them once in our whole application.
Manually taking care of this in the code adds an additional burden.

One possible solution is to externalize these tree definitions,
e.g., into a (maybe XML-like) configuration file,
and have some framework taking care of wiring the instances at runtime.

But fortunately, since we are using [static type hints](https://docs.python.org/3/library/typing.html)
for our constructor parameters,
we can avoid this manual work completely.
Instead, an appropriate framework can automatically deduce the graph.
We can then write something very simple:

```python
business = assemble(DomainLogic)
```

and let a provided `assemble` function do all the work.

`assemble` can recognize,
the types clearly stating that `domain.DomainLogic` needs a
`database_connection.Connection`,
thus it can construct and inject the dependency automagically.

One framework, providing such functionality,
is [enterprython](https://github.com/Dobiasd/enterprython).
Using it, we only need to annotate our "service" (`database_connection.Connection`)
with `@component()`. Then `assemble`, which is provided by the library,
can already do its thing, i.e., create our "client" (`domain.DomainLogic`).

```python
# database_connection.py
from enterprython import component

@component()
class Connection:
    ...
```

```python
# domain.py
from database_connection import Connection

class DomainLogic:
    def __init__(self, data_access: Connection):
        ...
```

```python
from enterprython import assemble
from domain import DomainLogic

if __name__ == '__main__':
    business = assemble(DomainLogic)
```

If the service (`database_connection.Connection` in that case) would itself
depend on other things, they also would be auto-created (singleton style)
in the libraries DI container, and then injected,
rinsing and repeating until the full dependency tree is resolved.
In case something is missing, an appropriate exception will be raised.

In addition to this minimal example, with enterprython we can also:

* work with abstract base classes, thus only [depend on abstractions](https://en.wikipedia.org/wiki/Dependency_inversion_principle).
* decide if services should be singletons or not.
* provide custom service factories.
* do some additional other stuff, see [enterprython's features list](https://github.com/Dobiasd/enterprython/#features).

Naturally, in our unit tests, we can still manually
constructor-inject a `MockConnection` into the `DomainLogic` object we want to test:

```python
domain_logic = DomainLogic(create_mock_connection())
```

Of course [enterprython](https://github.com/Dobiasd/enterprython)
might not be the only static-type-annotation-based
DI framework available for Python. In case, with this article, I was successful in
convincing you about the general usefulness of this pattern,
I'd like to encourage you to give it a try,
but also to check out other options too.
