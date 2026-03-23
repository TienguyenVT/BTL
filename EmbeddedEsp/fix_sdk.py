import os

if os.path.exists('sdkconfig'):
    with open('sdkconfig', 'r') as f:
        lines = f.readlines()
else:
    lines = []

new_lines = []
for l in lines:
    if not l.startswith('CONFIG_PARTITION_TABLE') and not l.startswith('CONFIG_ESPTOOLPY_FLASHSIZE'):
        new_lines.append(l)

new_lines.extend([
    'CONFIG_PARTITION_TABLE_CUSTOM=y\n',
    'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"\n',
    'CONFIG_PARTITION_TABLE_FILENAME="partitions.csv"\n',
    'CONFIG_PARTITION_TABLE_OFFSET=0x8000\n',
    'CONFIG_PARTITION_TABLE_MD5=y\n',
    'CONFIG_ESPTOOLPY_FLASHSIZE_2MB=y\n',
    'CONFIG_ESPTOOLPY_FLASHSIZE="2MB"\n'
])

with open('sdkconfig', 'w') as f:
    f.writelines(new_lines)
