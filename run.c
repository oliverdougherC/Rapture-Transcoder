#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

#define MAX_PATH 260
#define MAX_LINE 1024

// Global variables
char input_dir[MAX_PATH] = "~/media/trans_in";
char output_dir[MAX_PATH] = "~/media/trans_out";
char video_codec[20] = "x264";
char movie_output_directory[MAX_PATH] = "~/media/movies";
char tv_output_directory[MAX_PATH] = "~/media/tv_shows";
char omdb_api_key[MAX_LINE] = "";
int quality = 18;
int use_media_detection = 0;
int delete_original = 0;

#define MEDIA_ARGS_SIZE 2048

void trim(char *str) {
    char *end;
    while(isspace((unsigned char)*str)) str++;
    if(*str == 0) return;
    end = str + strlen(str) - 1;
    while(end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
}

int check_dependencies() {
    int result = system("python3 --version");
    if (result != 0) {
        printf("Python is not installed or not in PATH.\n");
        return 0;
    }
    result = system("ffmpeg -version");
    if (result != 0) {
        printf("FFmpeg is not installed or not in PATH.\n");
        return 0;
    }
    return 1;
}

void install_dependencies() {
    printf("Running setup script...\n");
    int result = system("./setup");
    if (result == 0) {
        printf("Setup completed successfully.\n");
    } else {
        printf("An error occurred during setup. Please check the output for details.\n");
    }
}

void start_transcoding() {
    char command[1024];
    snprintf(command, sizeof(command), 
             "python3 run_transcode.py --input \"%s\" --output \"%s\" --codec %s --crf %d",
             input_dir, output_dir, video_codec, quality);
    
    if (use_media_detection) {
        char media_detection_args[MEDIA_ARGS_SIZE];
        snprintf(media_detection_args, sizeof(media_detection_args),
                 " --use-media-detection --api-key %s --movies-dir \"%s\" --tv-shows-dir \"%s\"",
                 omdb_api_key, movie_output_directory, tv_output_directory);
        strcat(command, media_detection_args);
    }
    
    printf("Starting Rapture-Transcoder...\n");
    int result = system(command);
    if (result == 0) {
        printf("Transcoding completed successfully.\n");
    } else {
        printf("An error occurred during transcoding. Check the logs for details.\n");
    }
}

void view_logs() {
    printf("Opening log file...\n");
    system("xdg-open logs/transcoding.log");
}

void schedule_task() {
    char time[10];
    char interval[10];
    char cron_schedule[50];
    char command[1024];
    char *current_dir;
    int hours, result;
    
    printf("Enter the time to schedule the task (HH:MM): ");
    fgets(time, sizeof(time), stdin);
    trim(time);

    printf("Enter the number of hours between task runs (e.g., 12, 24, 168): ");
    fgets(interval, sizeof(interval), stdin);
    trim(interval);

    hours = atoi(interval);

    if (hours == 24) {
        snprintf(cron_schedule, sizeof(cron_schedule), "%s * * * *", time);
    } else if (hours == 168) {
        snprintf(cron_schedule, sizeof(cron_schedule), "%s * * * 0", time);
    } else {
        snprintf(cron_schedule, sizeof(cron_schedule), "%s */%d * * *", time, hours);
    }

    current_dir = getcwd(NULL, 0);
    if (current_dir == NULL) {
        perror("Failed to get current directory");
        return;
    }

    snprintf(command, sizeof(command), 
             "(crontab -l 2>/dev/null; echo \"%s %s/run\") | crontab -",
             cron_schedule, current_dir);
    free(current_dir);
    
    result = system(command);
    if (result == 0) {
        printf("Task scheduled successfully to run at %s, every %s hours.\n", time, interval);
    } else {
        printf("Failed to schedule task. Make sure you have permission to modify crontab.\n");
    }
}

int main() {
    char choice[10];
    int running = 1;
    
    while (running) {
        printf("\nRapture-Transcoder Menu:\n");
        printf("1. Start Transcoding\n");
        printf("2. Check Dependencies\n");
        printf("3. Run Setup\n");  // Changed this line
        printf("4. View Logs\n");
        printf("5. Schedule Transcoding Task\n");
        printf("6. Exit\n");
        printf("Enter your choice: ");

        fgets(choice, sizeof(choice), stdin);
        trim(choice);

        switch(atoi(choice)) {
            case 1:
                start_transcoding();
                break;
            case 2:
                if (check_dependencies()) {
                    printf("All dependencies are installed.\n");
                }
                break;
            case 3:
                install_dependencies();  // This now runs ./setup
                break;
            case 4:
                view_logs();
                break;
            case 5:
                schedule_task();
                break;
            case 6:
                running = 0;
                break;
            default:
                printf("Invalid choice. Please try again.\n");
        }
    }

    printf("Thank you for using Rapture-Transcoder!\n");
    return 0;
}