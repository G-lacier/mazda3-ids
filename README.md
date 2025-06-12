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
python ids_cli.py /path/to/IDS/root
```

The tool expects the IDS data directory as the only argument and will print
information extracted from the dataset.

### Example dataset layout

```
/path/to/IDS/root/
├── Data
│   ├── DataTypes.xml
│   ├── vehicle.xml
│   └── ...
└── XMLFiles
    └── Text
        └── ENG.xml
```

## Environment Setup

Install Python dependencies using `requirements.txt`:

```sh
pip install -r requirements.txt
```

## Tests

Basic unit tests can be executed with:

```sh
python -m unittest discover tests
```
