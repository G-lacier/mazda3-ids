CC=gcc
CFLAGS=-Wall -O2
LIBS=-lssl -lcrypto

PROGRAMS=decrypt encrypt exml fnp

all: $(PROGRAMS)

%: %.c
$(CC) $(CFLAGS) -o $@ $< $(LIBS)

clean:
rm -f $(PROGRAMS)
