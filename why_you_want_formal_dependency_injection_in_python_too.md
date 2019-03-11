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
        return max(self.data_access.get_all_customers(),
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
import database_connection
from customer import Customer

class DomainLogic:
    def __init__(self) -> None:
        self.data_access = DomainLogic.init_data_access()

    @staticmethod
    def init_data_access() -> database_connection.Connection:
        return database_connection.Connection()

    def most_valuable_customer(self) -> Customer:
        return max(self.data_access.get_all_customers(),
                   key=lambda customer: customer.value_in_dollars)

```

Now you need to unit test the complex implementation of your business logic.
For this you'll want to replace `data_access` with some mock.
In Python there are multiple options to do so.
A simple and common one, using monkey patching,
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
and thus step on each others toes.

Third, in case of multiple dependencies,
not all tests might need to patch the same number of things in the class.
Then, even with non-concurrent test execution,
this can end up in not correctly resetting the "state" of the class in some place
after one test, and subsequently invalidating other tests.
The overall success of the test suite
will depend on the order of execution of the test cases,
if not all developers take special care. Yikes!

In general one runs into the same problems as usual
when manually mutating (and depending on) some global state from different places.
In this case it's just not some normal runtime value
but the class itself which is mutated.

So the sane approach is to make the dependency explicit
by letting the constructor of `DomainLogic` take the data-access object to use
as a parameter:

```python
# domain.py
import database_connection

class DomainLogic:
    def __init__(self, data_access: database_connection.Connection):
        self.data_access = data_access

    def most_valuable_customer(self):
        return max(self.data_access.get_all_customers(),
                   key=lambda customer: customer.value_in_dollars)
```

Now you can instantiate it with whatever data source is suitable for any given situation:
```python
import database_connection

if __name__ == '__main__':
    business = DomainLogic(database_connection.Connection())
```

```python
class DomainLogicTest(unittest.TestCase):
    def test_most_valuable_customer(self) -> None:
        domain_logic = DomainLogic(create_mock_connection())
```

For this simple case the manual injection works fine.
But with larger, real-world dependency trees, we hit a problem.
For example just creating a `Controller` can become quite cumbersome: 

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
might need to be a singleton instance, i.e., we only want to instantiate
them once in our whole application.
Manually taking care of this adds an additional burden.

Defining all this in some external (maybe XML-like) configuration file is no better.

Coming back to our initial example,
ideally we would like to just say something like:

```python
business = assemble(DomainLogic)
```

and have some framework providing the `assemble` function to do all the work.

Since we fortunately annotated the parameters of our constructors with type hints,
it is actually possible for a framework to provide this functionality.

The types clearly state that `domain.DomainLogic` needs a
`database_connection.Connection`,
thus it should be possible to have it constructed and injected automagically.

And it is. For example,
if we use [enterprython](https://github.com/Dobiasd/enterprython)
as our DI framework,
we only need to annotate our "service" (`database_connection.Connection`)
with `@component()` and the also provided `assemble` can do it's thing,
i.e., create our "client" (`domain.DomainLogic`).

We can also:
* work with abstract base classes.
* provide custom factories.
* decide if services should be singletons or not.
* do much more, see [enterprython's features list](https://github.com/Dobiasd/enterprython/#features).

Of course in our unit test we can still manually
constructor-inject a `MockConnection` into the `DomainLogic` object we want to test.
