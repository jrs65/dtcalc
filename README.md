# dtcalc

A Python library for parsing and performing calculations involving times and durations,
inspired by the datetime picker in grafana.

## Installation

`dtcalc` can be installed directly from Github using pip:
```
pip install git+https://github.com/jrs65/dtcalc
```

## Usage

This package is designed for performing arithmetic operations on instances of time and
durations of time expressed as text. Only certain combinations make sense:

- Durations of time may be added or subtracted from an instance of time to form a new instance..
- Two instances of time may be subtracted to form a duration.
- Durations can be multiplied or divided by numbers to create a new duration.

Any thing else will throw an error.

Examples:
```python
>>> import dtcalc
>>> import datetime
>>> dtcalc.parse("2019-04-05T07:00:00Z + 4d").evaluate()
datetime.datetime(2019, 4, 9, 7, 0, tzinfo=datetime.timezone.utc)
>>> import datetime
>>> dtcalc.parse("now + 5 * 4d + 3h").evaluate(now=datetime.datetime(2023, 11, 10, 12, 0, 0))
datetime.datetime(2023, 11, 30, 15, 0)
```

This is particularly useful for parsing flexible user input into fully formed datetime
instances. This uses a custom written parser and is completely safe.

## Syntax

There are three dimensions of data understood by `dtcalc`. Datetime instances, durations and dimensionless numbers.

Operations are written using standard infix notation. `+`, `-`, `*`, `/` are all
supported for correct combinations of dimensions.

### Literals

There are three literal types, one for each dimension:
- Number literals are written in standard notation, e.g. `5` or `1.78`.
- Duration literals are a number with a duration suffix code, e.g. `1.5d` (36 hours) or
`15s` (15 seconds). Supported codes are week (`w`), day (`d`), hour (`h`), minute (`m`),
or second (`s`).
- Instance literals are written in full
[ISO8601](https://en.wikipedia.org/wiki/ISO_8601) format, e.g.
`2023-10-15T17:00:15+07:00`.

### Identifiers

A string may contain undefined identifiers that are always treated as instances, e.g.
`now`. The interpretation of these is up to the application but they must be defined
before calling `.evaluate()`.