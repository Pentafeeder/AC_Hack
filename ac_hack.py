import math
import sys
import tkinter as tk
import ctypes
import pymem 
from pymem.ptypes import RemotePointer 
import array
import vectormath as vmath
#import pyMeow as pm

# get our process
process_name = 'ac_client.exe'
process = pymem.Pymem(process_name)

# setup
alloc_mem_addr = process.allocate(0x12)

class address:
    FOV = process.base_address + 0x18A7CC
    player_ent_ptr = process.base_address + 0x18AC00 # should be 58AC00
    player_ent_addr = RemotePointer(process.process_handle, player_ent_ptr).value
    num_players = player_ent_ptr  + 0xC
    local_ent_list_ptr = player_ent_ptr + 0x04

    # menu FOV = process.base_address + 0x185884 -- need to resolve through multi-level pointer

class offsets:
    name = 0x205
    health = 0xEC
    FOV = [0x14, 0x1C, 0x20]
    
    team = 0x30C

    team_from_health = health - team #224

    ar_ammo = 0x140
    carbine_ammo = 0x130
    shotgun_ammo = 0x134
    subMG_ammo = 0x138
    grenade = 0x144
    special_pistol_ammo = 0x148
    handgun_ammo = 0x12c
    sniper_ammo = 0x13c

    south_north_axis = 0x2C
    z_axis = 0x30
    east_west_axis = 0x28

    camera_x = 0x34
    camera_y = 0x38

    head_pos_ew = 0x4
    head_pos_z = 0xC
    head_pos_ns = 0x8 

    ammo_dec = 0xC73EF
    #health sub = 0x1C223, 3 bytes

def infAmmo():
    process.write_bytes(process.base_address + offsets.ammo_dec, int('9090', 16).to_bytes(2, 'big'), 2) # writes 'nop' instruction to existing dec / store instruction
    print('you now have infinite ammo')
    pass

def changeValue(base_address, offset, increment):
    try:
        address = base_address + offset
        value = RemotePointer(process.process_handle, address).value
        value += increment
        process.write_int(address, value)
    except Exception as e:
        print('Given address is not a pointer, cannot convert')
        print(e)


def increaseHealth():
    changeValue(address.player_ent_addr, offsets.health, 1000)
    print('your health has increased')

def addGrenade():
    changeValue(address.player_ent_addr, offsets.grenade, 1)
    print('added grenade to inventory')

# for values stored in multi-level pointers like FOV
# obsolete, since I found the real FOV address
def traversePointers(base_address, offsets):
    address = RemotePointer(process.process_handle, base_address).value
    for offset in offsets:
        try:
            dereference = RemotePointer(process.process_handle, address + offset).value
            address = dereference
        except Exception as e:
            print('end of pointer')
            return address
    # by end, address is a primary value
    return address

def angle_between(v1, v2):
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    dot = max(min(dot, 1.0), -1.0)  # Clamp for precision
    angle_rad = math.acos(dot)
    angle_deg = math.degrees(angle_rad)
    return angle_deg

def trackOthers():
    player_addr = address.player_ent_addr
    ent_list_addr = RemotePointer(process.process_handle, address.local_ent_list_ptr).value
    enemy_addr = RemotePointer(process.process_handle, ent_list_addr).value
    if (enemy_addr == 0):
        enemy_addr = RemotePointer(process.process_handle, ent_list_addr + 0x4).value

    enemy_coords = [0, 0, 0] #x, y, z, (east/west, south/north, up/down)
    player_coords = [0, 0, 0]
    
    camera_x_deg = process.read_float(player_addr + offsets.camera_x)
    camera_y_deg = process.read_float(player_addr + offsets.camera_y)
    
    north_vector = vmath.Vector3(1, 0 , 0)
    x_rad = math.radians(camera_x_deg)
    dy = math.tan(x_rad)


    player_direction_vector = vmath.Vector3(1, dy, 0).normalize()

    # # camera vector
    # x_rad = math.radians(camera_x)
    # dx = math.sin(x_rad)
    # dz = math.cos(x_rad)


    print(hex(player_addr + offsets.head_pos_ew))
    enemy_coords[0] = process.read_float(enemy_addr + offsets.head_pos_ns)
    enemy_coords[1] = process.read_float(enemy_addr + offsets.head_pos_ew)
    enemy_coords[2] = process.read_float(enemy_addr + offsets.head_pos_z)
    
    player_coords[0] = process.read_float(player_addr + offsets.head_pos_ns)
    player_coords[1] = process.read_float(player_addr + offsets.head_pos_ew)
    player_coords[2] = process.read_float(player_addr + offsets.head_pos_z)

   
    
    # vectors between player and enemy
    vx = player_coords[0] - enemy_coords[0]
    vy = player_coords[1] - enemy_coords[1]
    vz = player_coords[2] - enemy_coords[2]

    enemy_player_vector = vmath.Vector3(vx, vy, 0).normalize()
    
    
    angle_a = math.atan2(vx, vy)
    angle_b = math.atan2(1, dy)
    
    angle_diff = angle_b - angle_a

    if angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    elif angle_diff < -math.pi:
        angle_diff += 2 * math.pi

    print('new angle:', math.degrees(angle_diff))
    
    dot = enemy_player_vector.dot(player_direction_vector)
    denom = player_direction_vector.length * enemy_player_vector.length
    angle = math.degrees(math.acos(dot / denom))
    print(enemy_player_vector, player_direction_vector)
    print(angle, camera_x_deg)
    
    print(vx, vy)
    # camera facing away from enemy when vy > 0
    if (vx < 0 and vy > 0) or (vx > 0 and vy > 0):
        # player right of enemy
        print('changing angles')
        print(angle, 360 - angle)
        angle = 360 - angle
        angle = camera_x_deg + angle
    else:
        angle = camera_x_deg - angle

    process.write_float(player_addr + offsets.camera_x, angle)
   # process.write_float(player_addr + offsets.camera_y, vertical_deg)

    # now find angle between direction and enemy



    # x = math.sin(angle_rad)
    # y = math.cos(angle_rad)
    # camera_vector_x = vmath.Vector3(x, y, 0).normalize()

    # print('dotting')
    # print(camera_vector_x.dot(enemy_player_vector_x))

    # print(vx, vy, vz)
    # # normalise vectors
    # # mag_v = math.sqrt(vx**2 + vy**2 + vz**2)
    # # vx /= mag_v
    # # vy /= mag_v
    # # vz /= mag_v
    # #print(vx, vy, vz)

    # horizontal_rad = math.atan2(vz, vx)
    # horizontal_deg = math.degrees(horizontal_rad)

    # # Pitch (vertical rotation)
    # distance_xz = math.sqrt(vx**2 + vz**2)
    # vertical_rad = math.atan2(vy, distance_xz)
    # vertical_deg = math.degrees(vertical_rad)

    # print(horizontal_deg, vertical_deg)
    # print(hex(player_addr))

    # dot = vx*dx + vy*dz
    # dot = max(min(dot, 1.0), -1.0)  # Clamp for precision
    # angle_rad = math.acos(dot)
    # angle_deg = math.degrees(angle_rad)
    
    # print(angle_deg) # horizontal


    

def changeFOV(value):    
    try:
        print(hex(address.FOV), float(value))
        process.write_float(address.FOV, float(value))
    except Exception as e:
        print('please input a positive number')

    pass

def makeInvulnerable(option):
    team_addr = RemotePointer(process.process_handle, address.player_ent_addr + offsets.team)
    # set team number
    if option == 'solo':
        team_addr = RemotePointer(process.process_handle, address.num_players)
    elif option != 'team':
        print('invalid option, defaulting to team')
    
    # change team for invulnerability
    process.write_bytes(address.player_ent_addr + offsets.team, int(f'{team_addr.value:0{2}x}', 16).to_bytes(2, 'big'), 2) # change team to match invulnerability 

    # inject code into malloced memory    
    process.write_bytes(alloc_mem_addr, int('83BB24020000' + f'{team_addr.value:0{2}x}', 16).to_bytes(7, 'big'), 7) # cmp dword ptr [ebx+00000224],00 
    process.write_bytes(alloc_mem_addr + 0x7, int('0F8405000000', 16).to_bytes(6, 'big'), 6) # je 00C30012
    process.write_bytes(alloc_mem_addr + 0xD, int('297304', 16).to_bytes(3, 'big'), 3) # sub [ebx+04],esi
    process.write_bytes(alloc_mem_addr + 0x10, int('8BC6', 16).to_bytes(2, 'big'), 2) # mov eax,esi
    
    
    
    
    # getting byte difference between mem addr of old instructions and mem addr of injected instructions
    opcode_bytes = str(alloc_mem_addr - process.base_address - 0x1C223 - 0x5)
    num_instruction_bytes = 0x12 # 18 bytes
    return_opcode = hex((~(int(bytes(opcode_bytes, 'utf-8')) + num_instruction_bytes + 0x5) & (2**32 - 1)) + 1).split('x')[1]
    opcode_bytes = hex(int(opcode_bytes)).split('x')[1]
    
    # get relative jump byte from address to new code
    opcode_bytes = 'E9' + swapEndianness(opcode_bytes)
    return_opcode = 'E9' + swapEndianness(return_opcode)
    
    #jump to injected code
    process.write_bytes(process.base_address + 0x1C223, int(opcode_bytes, 16).to_bytes(5, 'big'), 5) 
    
    #jump back to previous code and continue
    process.write_bytes(alloc_mem_addr + 0x12, int(return_opcode, 16).to_bytes(5, 'big'), 5) # jmp ac_client.exe+1C228
    print('you are now invincible')
               

def swapEndianness(string):
    if sys.byteorder != 'little':
        return string
    
    arr = ['00' for i in range(4)]
    print(string, len(string), len(string) // 2)
    for i in range(len(string) // 2):
        arr[len(string) // 2 - i - 1] = string[2*i] + string[2*i + 1]

    return ''.join(arr)

def main():
    while True:
        print("Type the number corresponding to what hack you want to have:")
        print("1. infinite ammo")
        print("2. increased health")
        print("3. wallhacks")
        print("4. aimbot")
        print('5. add grenade to inventory')
        print('6. become invulnerable')
        print('7. change FOV')
        hack = input("").strip()
        
        match hack:
            case '1':
                print('getting infinite ammo')
                infAmmo()
            case '2':
                print('getting increased health / invulnerability')
                increaseHealth()
            case '3':
                print('getting wallhacks')
            case '4':
                print('getting aimbot')
                trackOthers()
            case '5':
                print('getting grenade')
                addGrenade()
            case '6':
                option = input('type "team" or "solo" to include for invincibility: ')
                makeInvulnerable(option)
            case '7':
                value = input('type a positive number between 0 and 170 to set the FOV: ')
                changeFOV(value)
            case _:
                print('invalid hack')
        

if __name__ == "__main__":
    print("starting hack")
    try:
        main()
    finally:
        #free malloced memory and write back old instructions (if changed)
        process.free(alloc_mem_addr) 
        process.write_bytes(process.base_address + 0x1C223, int('2973048bc6', 16).to_bytes(5, 'big'), 5) 
