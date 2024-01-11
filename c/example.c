#include <stdlib.h>
#include <string.h>
#include <stdio.h>

const  char * caesarCiphered(unsigned char offset, const  char * clearText, unsigned  int textLength) {
	char * result = malloc(textLength); // Caller choose the right amount of memory to allocate
	// char * result = malloc(textLength * 3); Nothing would stop us if we tried to allocate more than necessary

	for(unsigned  int i = 0; i< textLength; i++) {
		result[i] = clearText[i] + offset;
	}

	return result;
}

int expectEqualStrings(const char* expected, const char* actual) {
    unsigned int len = strlen(expected);
    
    if(strlen(actual) != len)return -1;

    for(unsigned int i =0; i < len; i++) {
        if (expected[i] != actual[i]) return -1;
    }

    return 0;
}

int main(int argc, const char** args) {
    const char * input = "Xtlnqnx%wthpx&";
    const char * actual = caesarCiphered(251, input, 14);
    int test = expectEqualStrings("Sogilis rocks!", actual);
    if(test != 0) {
        printf("Expected '%s', got '%s'\n", "Sogilis rocks!", actual);
    }
    return test;
}
