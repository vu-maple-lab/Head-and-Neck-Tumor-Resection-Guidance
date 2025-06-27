from svo_processing import select_frame, process_svo

def main():
    """
    Main entry point of the SVO Frame Data Extractor tool.
    Provides an interactive interface to select a frame
    from the given SVO file and process it using SAM segmentation.
    """

    # TODO: Replace this with a command line argument or a config file
    svo_file = "path/to/your_file.svo" 

    while True:
        # Prompt the user for frame selection method
        user_choice = input(
            "Select frame manually (T) or enter a frame number (F)? "
        ).strip().upper()

        if user_choice == "T":
            # Use interactive frame selector
            frame_id = select_frame(svo_file)
            break
        elif user_choice == "F":
            try:
                frame_id = int(input("Enter Frame Number:"))
                break
            except ValueError:
                print("Please enter a valid integer frame number.")
        else:
            print("Invalid input. Please enter 'T' or 'F'.")

    print(f"Processing frame ID: {frame_id}")
    process_svo(svo_file, frame_id)


if __name__ == "__main__":
    main()
