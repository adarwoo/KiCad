#!/usr/bin/python3
import pcbnew

def get_holes_list(board):
    holes_list = []

    for pad in board.GetPads():
        print(dir(pad))
        name = pad.GetNet().GetNetname()
        if name == "Through Hole":
            holes_list.append( pad.GetPosition() )

    return holes_list

if __name__ == "__main__":
    pcb_file_path = "/home/eng/pulsegem/pulsegem.kicad_pcb"
    board = pcbnew.LoadBoard(pcb_file_path)

    holes = get_holes_list(board)

    if holes:
        for hole in holes:
            print(f"Hole at ({hole[0]} mils, {hole[1]} mils)")
    else:
        print("No holes found.")