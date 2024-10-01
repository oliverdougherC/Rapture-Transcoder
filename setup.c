#include <stdio.h>
#include <stdlib.h>

int install_requirements() {
    printf("Installing requirements...\n");
    
    //Install python3
    printf("Installing python3...\n");
    int python3_result = system("sudo apt install -y python3");
    if (python3_result != 0) {
        fprintf(stderr, "Error: Failed to install python3.\n");
        return 1;
    }

    // Install FFmpeg
    printf("Installing FFmpeg...\n");
    int ffmpeg_result = system("sudo apt install -y ffmpeg");
    
    if (ffmpeg_result != 0) {
        fprintf(stderr, "Error: Failed to install FFmpeg.\n");
        return 1;
    }
    
    //Install pip
    printf("Installing pip...\n");
    int pip_result = system("sudo apt install -y python3-pip");
    if (pip_result != 0) {
        fprintf(stderr, "Error: Failed to install pip.\n");
        return 1;
    }

    // Execute pip install command
    printf("Installing Python requirements...\n");
    int pip_install_result = system("pip install -r requirements.txt");
    
    if (pip_install_result == 0) {
        printf("All requirements installed successfully.\n");
        return 0;
    } else {
        fprintf(stderr, "Error: Failed to install Python requirements.\n");
        return 1;
    }
}

int main() {
    return install_requirements();
}
