# bp35a1_broute
python3 library of reading / writing data from smart meter (b route) with BP35A1

## usage
Before using this library, write `WOPT 01` to your BP35A1 in order to read UDP payload in ASCII format.

```
#!python3
from bp35a1 import BRouteReader

broute = BRouteReader("/dev/ttyAMA0") # serial port name
broute.connect("00000012345600000000000001234567", "012345678901") # id and password
power_cons = broute.read_moment_power_consumption()
print("power consumption : {:} W".format(power_cons))
```
