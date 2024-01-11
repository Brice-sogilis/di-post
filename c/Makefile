CC=gcc
CFLAGS=-Wall

tests: example.exe
	./example.exe

example.exe: example.o
	$(CC) $(CFLAGS) -o example.exe example.o

example.o: example.c
	$(CC) $(CFLAGS) -c -o example.o example.c
