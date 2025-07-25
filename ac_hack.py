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


def trackOthers():
    player_addr = address.player_ent_addr
    ent_list_addr = RemotePointer(process.process_handle, address.local_ent_list_ptr).value
    enemy_addr = RemotePointer(process.process_handle, ent_list_addr).value
    if (enemy_addr == 0):
        enemy_addr = RemotePointer(process.process_handle, ent_list_addr + 0x4).value

    enemy_coords = [0, 0, 0] #x, y, z, (east/west, south/north, up/down)
    player_coords = [0, 0, 0]
    
    
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

    distance = math.sqrt(vx**2 + vy**2 + vz**2)

    print('The distance between you and an enemy is:', distance)
    if (distance > 30):
        print('you are far from them')
    elif (distance > 15):
        print('you are quite near them')
    else:
        print('very close!!!')
    
    


    

def changeFOV(value):    
    try:
        print(hex(address.FOV), float(value))
        process.write_float(address.FOV, float(value))
    except Exception as e:
        print('please input a positive number')


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
        print("3. get distance")
        print('4. add grenade to inventory')
        print('5. become invulnerable')
        print('6. change FOV')
        hack = input("").strip()
        
        match hack:
            case '1':
                print('getting infinite ammo')
                infAmmo()
            case '2':
                print('getting increased health / invulnerability')
                increaseHealth()
            case '3':
                print('tracking distance')
                trackOthers()
            case '4':
                print('getting grenade')
                addGrenade()
            case '5':
                option = input('type "team" or "solo" to include for invincibility: ')
                makeInvulnerable(option)
            case '6':
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
