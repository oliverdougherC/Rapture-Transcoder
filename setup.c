#include <stdio.h>
#include <stdlib.h>

int main() {
    int result;

    // Run the Python setup script
    result = system("python3 setup.py");
    if (result != 0) {
        fprintf(stderr, "Error: Python setup script failed.\n");
        return 1;
    }

    // Rest of your setup code goes here
    // ...

    return 0;
}
