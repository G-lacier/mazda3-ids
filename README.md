# Mazda IDS Parser

This project provides utilities for extracting information from Mazda IDS XML datasets.

## Building C utilities

A simple `Makefile` is provided to build helper programs. Run:

```sh
make
```

This requires a C compiler and OpenSSL development libraries.

## Running the parser

After building, you can invoke the parser with Python:

```sh
python ids.py /path/to/IDS/root
```

The tool expects the IDS data directory as the only argument and will print
information extracted from the dataset.

## Tests

Basic unit tests can be executed with:

```sh
python -m unittest discover tests
```


