#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
~~ Scheduling conflict solver~~

Outputs all possible combinations for your weekly schedule! 
Just provide one definition file for each subject, named subjectname.txt, 
placed inside a folder ./subjects/, and formatted the following way:

UE
Di 8:00-9:30
Do 10:00-11:30

or

VO
Mo 11:00-12:30
Di 11:00-12:30
Mi 11:00-12:00

- "UE" type subjects will be treated as requiring exactly ONE of the time slots
  listed
- "VO" subjects will strive to fill ALL the time slots (but less-than-perfect
  schedules where individual VO slots are skipped will be saved anyway)

Optional:
- location
- color for the subject's graphical representation
  (as either HTML color name or hex code or tuple of RGB values from 0-255)
e.g.:

UE
steelblue / #4682b4 / 70,130,180
Di 8:00-9:30 Audimax
Do 10:00-11:30 other place

Output will be saved in ./schedules/
"""

import sys, os, re, glob, itertools, threading
import numpy as np
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageColor
from time import sleep

in_dir_name  = "subjects"
out_dir_name = "schedules"

start_of_day = 8
end_of_day   = 20

weekdays = {
            0:"Montag",
            1:"Dienstag",
            2:"Mittwoch",
            3:"Donnerstag",
            4:"Freitag",
            5:"Samstag",
            6:"Sonntag"
}
abbreviation_length = 2

text_file          = False
ascii_calendar     = False
graphical_calendar = True

class Schedule:
    def __init__(self, **kwargs):
        try:
            self.table = kwargs['table']
        except KeyError:
            self.table = self.create_schedule(kwargs['subjects'],
                                              kwargs['allocations'])
    
    def create_schedule(self, subjects, allocations):
        print("creating new schedule ...")
        
        newsched = Schedule.empty_schedule()
        
        for i in range(len(subjects)):
            for j in range(len(subjects[i].times)):
                if allocations[i].array[j]:
                    subject = subjects[i]
                    selected_time = subject.times[j]
                    if Schedule.is_free(newsched, selected_time):
                        Schedule.fill(newsched, subject, selected_time)
                        subject.mark_allocated(selected_time)
        
        for subject in subjects:
            if subject.type == "VO":
                for selected_time in subject.times:
                    if (
                        selected_time not in subject.allocated_times and
                        Schedule.is_free(newsched, selected_time)
                    ):
                        Schedule.fill(newsched, subject, selected_time)
                        subject.mark_allocated(selected_time)
        
        self.is_incomplete = False
        total_failure      = False
        
        for subject in subjects:
            if not subject.is_partially_complete():
                total_failure = True
            elif not subject.is_complete():
                self.is_incomplete = True
            subject.reset()
        
        if not total_failure:
            return newsched
        else:
            print("abandoning: failed to include all subjects\n")
            return
    
    def __eq__(self, other):
        return self.table == other.table
    
    def empty_schedule():
        sched = dict()
        for day in range(day0, day0 + 5):
            for hh in range(start_of_day, end_of_day):
                for mm in range(0, 60, 5):
                    sched[datetime(year,month,day,hh,mm)] = ""
        return sched
    
    def is_free(schedule, selected_time):
        t = selected_time[0]
        while t < selected_time[1]:
            if schedule[t]: return False
            t += timedelta(minutes=5)
        return True
    
    def fill(schedule, subject, selected_time):
        t = selected_time[0]
        while t < selected_time[1]:
            schedule[t] = subject.name
            t += timedelta(minutes=5)

class Subject:
    name_pattern = re.compile(r"(.+)\.txt$")
    time_loc_pattern = re.compile(
        r"^(\w+)\W?\s+(\d{1,2})[:.](\d\d)-(\d{1,2})[:.](\d\d)\W?(\s+)?(.+)?$")
    ue_pattern = re.compile(r"[Uu][Ee]")
    vo_pattern = re.compile(r"[Vv][Oo]")
    color_tuple_pattern = re.compile(
        r"^\(?(\d{1,3})\)? ?\W? ?\(?(\d{1,3})\)? ?\W? ?\(?(\d{1,3})\)?$")
    color_string_pattern = re.compile(r"(^#[\dA-Fa-f]{3,6}$|^[A-Za-z]+$)")
    
    def __init__(self, filename):
        self.name      = re.search(Subject.name_pattern, filename).group(1)
        self.times     = list()
        self.locations = list()
        self.type      = ""
        self.color     = (127,127,127)
        with open("./"+in_dir_name+"/"+filename, "r") as fh:
            line = fh.readline().rstrip()
            if re.search(Subject.ue_pattern, line):
                self.type = "UE"
            elif re.search(Subject.vo_pattern, line):
                self.type = "VO"
            else:
                print("\nerror: subject '"+self.name+"'doesn't have a "
                      +"recognizable type\n")
                sys.exit()
            line = fh.readline().rstrip()
            if re.search(Subject.color_tuple_pattern, line):
                cmatch = re.search(Subject.color_tuple_pattern, line)
                self.color = (int(cmatch.group(1)), int(cmatch.group(2)),
                              int(cmatch.group(3)))
                skip_reading = 0
            elif re.search(Subject.color_string_pattern, line):
                self.color = line
                skip_reading = 0
            else:
                skip_reading = 1
            n = 0
            while line:
                if n >= skip_reading:
                    line = fh.readline().rstrip()
                if line:
                    match = re.search(Subject.time_loc_pattern, line)
                    if match:
                        try:
                            day = day0 + weekday_number(match.group(1))
                        except TypeError:
                            print("\nerror: wrong weekday format at subject '"
                                  +self.name+"'\n")
                            sys.exit()
                        begh = int(match.group(2))
                        begm = int(match.group(3))
                        endh = int(match.group(4))
                        endm = int(match.group(5))
                        self.times.append((datetime(year,month,day,begh,begm),
                                           datetime(year,month,day,endh,endm)))
                        if match.group(7):
                            self.locations.append(match.group(7))
                        else:
                            self.locations.append("")
                    else:
                        print("\nerror: times/location of subject '"+self.name
                              +"' can't be read\n")
                        sys.exit()
                n += 1
        self.start_times = [element[0] for element in self.times]
        self.allocated_times = set()
    
    def mark_allocated(self, selected_time):
        self.allocated_times.add(selected_time)
    
    def is_complete(self):
        if self.type == "VO":
            return self.allocated_times == set(self.times)
        else:
            return len(self.allocated_times) >= 1
    
    def is_partially_complete(self):
        return len(self.allocated_times) >= 1
    
    def reset(self):
        self.allocated_times = set()

class Allocation:
    def __init__(self, subject):
        self.index = 0
        self.has_reached_end = False
        self.__array = list()
        tmp = itertools.product([True, False], repeat=len(subject.times))
        if subject.type == "VO":
            for booltuple in tmp:
                if any(booltuple):
                    self.__array.append(booltuple)
        else:
            for booltuple in tmp:
                if sum(booltuple) == 1:
                    self.__array.append(booltuple)
    
    def get_array(self):
        return self.__array[self.index]
    
    def advance(self):
        if self.index < len(self.__array) - 1:
            self.index += 1
        else:
            self.has_reached_end = True
    
    def reverse(self):
        if self.index > 0:
            self.index -= 1
    
    def reset_end_status(self):
        self.has_reached_end = False
    
    array = property(get_array)

def weekday_number(weekday):
    for i in range(7):
        if re.match(weekday_patterns[i], weekday): return i

def setup(in_dir_name, out_dir_name):
    subject_dir        = "."+slash+in_dir_name+slash
    schedule_dir       = "."+slash+out_dir_name+slash
    local_files        = glob.glob("*")
    filename_pattern   = re.compile(r"\."+slash+slash2+in_dir_name
                                    +slash+slash2+r"(.*)")
    subject_file_paths = glob.glob(subject_dir+"*.txt")
    
    if subject_file_paths:
        print("loading subject definitions from "+subject_dir+" ...")
        subject_file_names = [re.search(filename_pattern, path).group(1)
                              for path in subject_file_paths]
        subjects = [Subject(file) for file in subject_file_names]
    else:
        print("\nerror: no subject definition files found\n"
              +"please place them inside "+subject_dir+"\n")
        if not in_dir_name in local_files:
            os.popen("mkdir "+subject_dir)
        sys.exit()
    
    if out_dir_name in local_files:
        print("cleaning up in "+schedule_dir+" ...\n")
        os.popen(delcmd+" "+schedule_dir+"*")
    else:
        print("creating schedule directory under "+schedule_dir+" ...\n")
        os.popen("mkdir "+schedule_dir)
    
    sleep(1)
    
    return subjects

def percolate(subjects, allocations):
    for i in range(len(allocations)):
        if allocations[i].has_reached_end:
            allocations[i].reset_end_status()
            return
    
    global permutations
    perm_check_list = list()
    for element in allocations:
        perm_check_list.append(element.array)
    perm_check = tuple(perm_check_list)
    if perm_check in permutations:
        return
    else:
        permutations.add(perm_check)
    
    global saved_schedules, duplicates, version
    schedule  = Schedule(subjects = subjects, allocations = allocations)
    failed    = False
    duplicate = False
    try:
        if any([schedule == element for element in saved_schedules]):
            duplicate = True
            duplicates += 1
            print("abandoning: duplicate of existing schedule\n")
    except (AttributeError, TypeError):
        failed = True
    if not schedule.table: failed = True
    
    if not duplicate and not failed:
        if not schedule.is_incomplete:
            print("schedule successfully completed!")
        else:
            print("schedule created with at least one lecture incomplete")
        version += 1
        saved_schedules.append(schedule)
        if text_file:
            plain_write(schedule)
        if ascii_calendar:
            fancy_write(schedule)
        if graphical_calendar:
            create_graphical_calendar(schedule, subjects)
        print()
    
    for i in range(len(allocations)):
        allocations[i].advance()
        percolate(subjects, allocations)
        allocations[i].reverse()

def create_filename(schedule):
    global version
    if schedule.is_incomplete:
        completeness = "_INCOMPLETE_"
    else:
        completeness = ""
    return "schedule"+str(version)+completeness

def plain_write(schedule):
    schedule_dir = "./"+out_dir_name+"/"
    schedule_filename = create_filename(schedule)+".txt"
    print("saving as "+schedule_dir+schedule_filename)
    with open(schedule_dir + schedule_filename, "w") as fh:
        for step in schedule.table:
            fh.write(weekday_abbrevs[step.weekday()]+" "
                     +re.search(dtpattern, str(step)).group(1)
                     +" "+schedule.table[step]+"\n")

def fancy_write(schedule):
    field_width  = 25
    schedule_dir = "./"+out_dir_name+"/"
    schedule_filename = create_filename(schedule)+"ascii.txt"
    row          = "{0:^" + str(field_width) + "s}"
    toprow       = "      "
    for i in range(5):
        toprow += "{"+str(i)+":^"+str(field_width)+"s}"
    toprow += "\n"
    
    print("saving as "+schedule_dir+schedule_filename)
    with open(schedule_dir + schedule_filename, "w") as fh:
        t = datetime(year,month,day0,start_of_day)
        fh.write(toprow.format(*weekdays.values()))
        while t.hour < end_of_day:
            fh.write("{0:6s}".format(re.search(dtpattern, str(t)).group(1)))
            d = 0
            while d < 5:
                fh.write(row.format(schedule.table[t]))
                t += timedelta(days=1)
                d += 1
            fh.write("\n")
            t += timedelta(days=-5, minutes=5)

def create_graphical_calendar(schedule, subjects):
    schedule_dir = "./"+out_dir_name+"/"
    schedule_filename = create_filename(schedule)+".png"
    print("saving graphical calendar as "+schedule_dir+schedule_filename)
    
    res_x          = 1200
    res_y          = 740
    top_row        = 22
    first_column   = 70
    celltxt_offset = (3,3)
    bg_color       = "white"
    line_color     = "#cccccc"
    labeltxt_color = "black"
    celltxt_color1 = "white"   # for dark background
    celltxt_color2 = "black"   # for light background
    
    try:
        fnt1 = ImageFont.truetype('arial.ttf', 15)
        fnt2 = ImageFont.truetype('arial.ttf', 12)
    except OSError:
        try:
            fnt1 = ImageFont.truetype('Pillow/Tests/fonts/FreeSans.ttf', 16)
            fnt2 = ImageFont.truetype('Pillow/Tests/fonts/FreeSans.ttf', 13)
        except OSError:
            fnt1 = ImageFont.load_default()
            fnt2 = ImageFont.load_default()
    
    img  = Image.new("RGB", (res_x, res_y), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # map x coordinates to days
    x_begofday = np.linspace(first_column, res_x, 6)
    
    # map y coordinates to times
    y_begoftime = dict()
    y_row = np.linspace(top_row, res_y, 12*(end_of_day - start_of_day) + 1)
    t = datetime(year, month, day0, start_of_day)
    i = 0
    while t <= datetime(year, month, day0, end_of_day):
        y_begoftime[t] = y_row[i]
        i += 1
        t += timedelta(minutes=5)
    
    # draw horizontal lines
    t = datetime(year, month, day0, start_of_day)
    while t < datetime(year, month, day0, end_of_day):
        draw.line([(0, y_begoftime[t]), (res_x, y_begoftime[t])],
                   fill = line_color)
        t += timedelta(minutes=15)
    
    # draw vertical lines
    for i in range(5):
        draw.line([(x_begofday[i],0), (x_begofday[i],res_y)], fill=line_color)
    
    # label top row with weekdays
    day_width = (res_x - first_column) / 5
    for i in range(5):
        w, h = draw.textsize(weekdays[i], font=fnt1)
        draw.text((x_begofday[i] + (day_width - w)/2, 3), weekdays[i],
                  fill=labeltxt_color, font=fnt1)
    
    # label first column with times
    t = datetime(year, month, day0, start_of_day)
    while t < datetime(year, month, day0, end_of_day):
        t_end = t + timedelta(minutes=15)
        time_str = re.search(dtpattern, str(t)).group(1)+"-"+re.search(
                   dtpattern, str(t_end)).group(1)
        w, h = draw.textsize(time_str, font=fnt2)
        x = (first_column - w)/2
        y = y_begoftime[t] + (y_begoftime[t_end] - y_begoftime[t] - h)/2
        draw.text((x,y), time_str, fill=labeltxt_color, font=fnt2)
        t += timedelta(minutes=15)
    
    # fill calendar
    subject_dict = dict()
    for subject in subjects:
        subject_dict[subject.name] = subject
    
    for step in schedule.table:
        if schedule.table[step]:
            subj_name = schedule.table[step]
            subj = subject_dict[subj_name]
            try:
                i = subj.start_times.index(step)
                subj_times = subj.times[i]
                subj_location = subj.locations[i]
                
                if type(subj.color) == str:
                    (r,g,b) = ImageColor.getrgb(subj.color)
                else:
                    (r,g,b) = subj.color
                if np.sqrt(0.299*r**2 + 0.587*g**2 + 0.114*b**2)/255 < 0.75:
                    celltxt_color = celltxt_color1
                else:
                    celltxt_color = celltxt_color2
                    
                d = step.weekday()
                rect_beg_x = x_begofday[d] + 1
                rect_beg_y = y_begoftime[subj_times[0]-timedelta(days=d)] + 1
                rect_end_x = x_begofday[d+1] - 1
                rect_end_y = y_begoftime[subj_times[1]-timedelta(days=d)] - 1
                draw.rectangle([(rect_beg_x, rect_beg_y),
                                (rect_end_x, rect_end_y)],
                               fill = subj.color)
                
                w, h = draw.textsize(subj_name, font=fnt1)
                
                if rect_end_y - rect_beg_y <= 2 * (h + celltxt_offset[1]):
                    celltxto = (celltxt_offset[0], 1)
                else:
                    celltxto = celltxt_offset
                
                x = rect_beg_x + (day_width - w)/2
                y = rect_beg_y + celltxto[1] - 1
                draw.text((x,y), subj_name, fill=celltxt_color, font=fnt1)
                
                time_str = (
                    re.search(dtpattern, str(subj_times[0])).group(1)
                    +" - "+re.search(dtpattern, str(subj_times[1])).group(1)
                )
                w, h = draw.textsize(time_str, font=fnt1)
                x = rect_beg_x + celltxto[0]
                y = rect_end_y - h - celltxto[1]
                draw.text((x,y), time_str, fill=celltxt_color, font=fnt1)
                
                try:
                    w, h = draw.textsize(subj_location, font=fnt1)
                    x = rect_end_x - w - celltxto[0]
                    draw.text((x,y), subj_location, fill=celltxt_color,
                              font=fnt1)
                except SystemError:
                    pass
            
            except ValueError:
                pass
    
    img.save(schedule_dir+schedule_filename)
    
    global version
    if version <= 5:
        prev_stack_size = threading.stack_size()
        displaythread = threading.Thread(target=display_calendar, args=(img,))
        displaythread.start()
        threading.stack_size(prev_stack_size)

def display_calendar(image):
    image.show()

if os.name == "nt":
    slash = "\\"
    slash2 = slash
    delcmd = "del /q"
    custom_stack_size = 256 * 2**20 - 1 # 256 MiB = Windows limit
    custom_rec_limit  = 350000    # empirical max: 91162 at  64 MiB stack size
else:                             #               182343 at 128 MiB
    slash = "/"
    slash2 = ""
    delcmd = "rm -f"
    custom_stack_size = 512 * 2**20
    custom_rec_limit  = 700000

dtpattern = re.compile(r"\d\d-\d\d-\d\d (\d\d:\d\d):\d\d")

weekday_abbrevs = dict()
for i in range(7):
    weekday_abbrevs[i] = weekdays[i][:abbreviation_length]

weekday_patterns = list()
for i in range(7):
    daystr = weekdays[i]
    tmp = ""
    for j in range(abbreviation_length):
        tmp += "["+daystr[j]+daystr[j].swapcase()+"]"
    pat = re.compile(tmp+"("+daystr[abbreviation_length:]+")?$")
    weekday_patterns.append(pat)

year  = 2017
month = 10
day0  = 2

version         = 0
duplicates      = 0
saved_schedules = list()
permutations    = set()
subjects        = setup(in_dir_name, out_dir_name)

threading.stack_size(custom_stack_size)
old_rec_limit = sys.getrecursionlimit()
sys.setrecursionlimit(custom_rec_limit)
thread = threading.Thread(target = percolate, args = (subjects,
                [Allocation(subject) for subject in subjects]))
thread.start()
thread.join()
sleep(1)
sys.setrecursionlimit(old_rec_limit)
threading.stack_size()

incompletes = 0
for schedule in saved_schedules:
    if schedule.is_incomplete:
        incompletes += 1

n = len(saved_schedules)
if n == 1:
    sched_str = "schedule"
else:
    sched_str = "schedules"
if duplicates == 1:
    dupl_str = "duplicate"
else:
    dupl_str = "duplicates"
print("created "+str(n)+" "+sched_str+", of which "+str(incompletes)
      +" incomplete (plus "+str(duplicates)+" "+dupl_str+")")