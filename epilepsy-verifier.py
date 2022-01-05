from sys import argv

if len(argv) < 2:
    print("Which video?")
    exit()

# PROLOG
# PRZYGOTOWANIE DANYCH

from decord import VideoReader, cpu
from enum import Enum
from math import ceil
import time
import csv


# check this out:
# https://www.hardingfpa.com/technical-support/how-to-interpret-hardingfpa-results/
class Color(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2


def show_time(sec):
    ty_res = time.gmtime(sec)
    res = time.strftime("%H:%M:%S", ty_res)
    return res


file = argv[1]
red_coefficient = 3
flash_threshold = 0.5
try:
    vr = VideoReader(file, ctx=cpu(0))
except RuntimeError:
    exit()

video_height = vr[0].shape[0]
video_width = vr[0].shape[1]

# może nie warto badać wszystkich pikseli w klatce,
# ale zrobić siatkę 10x10
# będzie wtedy o 99% szybciej
height = 10
width = 10
grid_height = []
grid_width = []

potrzebie = video_height / (height + 1)
for i in range(height):
    grid_height.append(ceil((i + 1) * potrzebie))

potrzebie = video_width / (width + 1)
for i in range(width):
    grid_width.append(ceil((i + 1) * potrzebie))

number_of_frames = len(vr)
fps = vr.get_avg_fps()
maximum_flash_value = height * width * 3 * 255

vr.seek_accurate(0)

previous_frame = vr.next().asnumpy()
output_file = open(file + "_output.csv", "w")
output_file.write("0,0\n")

is_bad = False

total_time = time.time()

# AKT I
# LICZENIE FILMU

for frames in range(number_of_frames - 1):
    difference_between_frames = 0
    frame = vr.next().asnumpy()
    for row in grid_height:
        for column in grid_width:
            for color in Color:
                previous = previous_frame[row][column][color.value]
                current = frame[row][column][color.value]
                difference = abs(int(previous) - int(current))
                if color == Color.RED:
                    difference_between_frames += red_coefficient * difference
                else:
                    difference_between_frames += difference

    flash_value = round(difference_between_frames / maximum_flash_value, 3)
    if not is_bad and flash_value > 1:
        print("\nInteresting...")
        is_bad = True
    line_of_data = str(frames + 1) + "," + str(flash_value) + "\n"
    output_file.write(line_of_data)

    print("\rRemaining frames:", str(frames), "/", str(number_of_frames), end="")
    previous_frame = frame
total_time = time.time() - total_time
output_file.close()
print("\nTotal elapsed time:", show_time(total_time))

# AKT II
# BADANIE CSV

# wyznaczymy tablicę w której przechowywane są numery klatek w których są błyski
tab = []

with open(file + "_output.csv", "r") as plikCSV:
    reader = csv.reader(plikCSV)

    for row in reader:
        flash_value = float(row[1])
        if flash_value > flash_threshold:
            tab.append(int(row[0]))

# ANTRAKT
# GDZIE SĄ BŁYSKI

if len(tab) == 0:
    print("Looks good to me!")
    exit()

# print("Flashes occur at the following frames:")
# for a in tab:
#    print(str(a))

# AKT III
# SZUKANIE ZAGROŻENIA

# błyski nie mogą występować częściej niż 3Hz
# https://www.w3.org/TR/WCAG21/#seizures-and-physical-reactions
max_frequency = 3

# tablica krotek przechowywanych w taki sposób:
# (klatka od której zaczynają się niebezpieczne błyski, klatka w której kończą się błyski)
ranges_of_concern = []

i = 0
frame_of_concern = -1
while i < len(tab) - 2:
    j = i + 1
    while j < i + max_frequency:
        # jeżei obraz miga
        if tab[j] < tab[i] + fps:
            j = j + 1
        else:
            if frame_of_concern != -1:
                ranges_of_concern.append((frame_of_concern, tab[j-1]))
            frame_of_concern = -1
            break
    else:
        if frame_of_concern == -1:
            frame_of_concern = tab[i]
        j = j - 1
        i = j
    if frame_of_concern == -1:
        i = i + 1

if frame_of_concern != -1:
    ranges_of_concern.append((frame_of_concern, tab[j]))

# EPILOG
# OGŁOSZENIE WYNIKÓW

if len(ranges_of_concern) == 0:
    print("Seems OK")
    exit()

spf = 1/fps

print("Ranges of times of concern:")
for v_range in ranges_of_concern:
    start = v_range[0] * spf
    end = v_range[1] * spf
    print(show_time(start) + " - " + show_time(end))

# vr - dostęp do wideo
# vr[i] - dostęp do poszczególnych klatek wideo
# jest typu decord.ndarray.NDArray
# wewnątrz elementów jest takie ułożenie
# [ 81 52 48 ]
# [ R  G  B  ]
# czytamy jak w książce
# np.
# [[[135 156 165] wiersz.1 kolumna.1
#  [135 156 165] kolumna.2
#  [135 156 165] kolumna.3
#  ...
#  [ 96  68  41] kolumna.n-2
#  [ 96  68  41] kolumna.n-1
#  [ 96  68  41]]wiersz.1 kolumna.n
#
# [[135 156 165] wiersz.2 kolumna.1
#  [135 156 165] kolumna.2
#  [135 156 165] kolumna.3
#  ...
#  [ 96  68  41] kolumna.n-2
#  [ 96  68  41] kolumna.n-1
#  [ 96  68  41]]wiersz.2 kolumna.n
#
# ...
#
# [[249 137  70] wiersz.m-1 kolumna.1
#  [249 137  70] kolumna.2
#  [249 137  70] kolumna.3
#  ...
#  [ 84  55  49] kolumna.n-2
#  [ 82  53  49] kolumna.n-1
#  [ 81  52  48]]wiersz.m-1 kolumna.n
#
# [[249 137  70] wiersz.m kolumna.1
#  [249 137  70] kolumna.2
#  [249 137  70] kolumna.3
#  ...
#  [ 84  55  49] kolumna.n-2
#  [ 82  53  49] kolumna.n-1
#  [ 81  52  48]]]wiersz.m kolumna.n
