from svo_processing import select_frame, process_svo

if __name__ == "__main__":
    svo_files = r"C:\Users\qingyun\Desktop\preprocess\data\Pt_0000039\1039\cav.svo2"
    # svo_files = r"C:\Users\qingyun\Desktop\test.svo2"

    while True:
        ifSelectFrame = input("Select frame manually (T) or enter a frame number (F)? ")
        if ifSelectFrame == "T":
            frame_id = select_frame(svo_files)
            break
        elif ifSelectFrame == "F":
            frame_id = int(input("Enter Frame Number:"))
            break
        else:
            print("Invalid input. Please enter 'T' or 'F'.")

    print(frame_id)
    process_svo(svo_files, frame_id)