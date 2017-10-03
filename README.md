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
