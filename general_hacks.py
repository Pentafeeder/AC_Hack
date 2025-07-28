import sys
import pymem 
from pymem.ptypes import RemotePointer 
import math
from pynput import keyboard
from pynput.keyboard import Listener as KeyListener


# get our process
process_name = 'ac_client.exe'
process = pymem.Pymem(process_name)
base_address = process.base_address

# setup
alloc_mem_addr = process.allocate(0x12)


print(base_address)

class address:
    FOV = base_address + 0x18A7CC
    player_ent_ptr = base_address + 0x18AC00 # should be 58AC00
    player_ent_addr = RemotePointer(process.process_handle, player_ent_ptr).value
    num_players = player_ent_ptr  + 0xC
    local_ent_list_ptr = player_ent_ptr + 0x04
    traceline_func = 0x509010 
    print(player_ent_ptr, player_ent_addr)

class offsets:
    name = 0x205
    health = 0xEC   
    team = 0x30C

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

    auto_fire = 0x204
    current_weapon_ent = 0x368
    current_weapon_id = 0x4 # from current weapon ent

    ammo_dec = 0xC73EF
    health_sub = 0x1C223
    recoil = 0xC2EC3 


def removeRecoil():
    process.write_bytes(base_address + offsets.recoil, int('90'*5, 16).to_bytes(5, 'big'), 5) # writes 'nop' instruction to existing dec / store instruction
    print('recoil removed')

def infAmmo():
    process.write_bytes(base_address + offsets.ammo_dec, int('9090', 16).to_bytes(2, 'big'), 2)
    print('you now have infinite ammo')

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

def changeFOV(value):    
    try:
        process.write_float(address.FOV, float(value))
        print('fov changed')
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
    print(int(f'{team_addr.value:0{2}x}', 16))
    print(int(f'{team_addr.value:0{2}x}', 16).to_bytes(1, 'big'))
    print(int(f'{team_addr.value:0{2}x}', 16).to_bytes(1, 'little'))

    process.write_bytes(address.player_ent_addr + offsets.team, int(f'{team_addr.value:0{2}x}', 16).to_bytes(1, 'big'), 1) # change team to match invulnerability 

    # inject code into malloced memory    
    process.write_bytes(alloc_mem_addr, int('83BB24020000' + f'{team_addr.value:0{2}x}', 16).to_bytes(7, 'big'), 7) # cmp dword ptr [ebx+00000224],00 
    process.write_bytes(alloc_mem_addr + 0x7, int('0F8405000000', 16).to_bytes(6, 'big'), 6) # je 00C30012
    process.write_bytes(alloc_mem_addr + 0xD, int('297304', 16).to_bytes(3, 'big'), 3) # sub [ebx+04],esi
    process.write_bytes(alloc_mem_addr + 0x10, int('8BC6', 16).to_bytes(2, 'big'), 2) # mov eax,esi
    
    # getting byte difference between mem addr of old instructions and mem addr of injected instructions
    opcode_bytes = str(alloc_mem_addr - base_address - offsets.health_sub - 0x5)
    num_instruction_bytes = 0x12 # 18 bytes
    return_opcode = hex((~(int(bytes(opcode_bytes, 'utf-8')) + num_instruction_bytes + 0x5) & (2**32 - 1)) + 1).split('x')[1]
    opcode_bytes = hex(int(opcode_bytes)).split('x')[1]
    
    # get relative jump byte from address to new code
    opcode_bytes = 'E9' + swapEndianness(opcode_bytes)
    return_opcode = 'E9' + swapEndianness(return_opcode)
    
    #jump to injected code
    process.write_bytes(base_address + offsets.health_sub, int(opcode_bytes, 16).to_bytes(5, 'big'), 5) 
    
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

def clearHacks():
    process.write_bytes(base_address + offsets.health_sub, int('2973048bc6', 16).to_bytes(5, 'big'), 5) 
    process.write_bytes(base_address + offsets.ammo_dec, int('FF08', 16).to_bytes(2, 'big'), 2)
    process.write_bytes(base_address + offsets.recoil, int('F30F115638', 16).to_bytes(5, 'big'), 5) 
    print('hacks cleared')


def on_press(key):
    try: 
        match key:
            case keyboard.Key.f1:
                print('getting infinite ammo')
                infAmmo()
            case keyboard.Key.f2:
                print('getting increased health / invulnerability')
                increaseHealth()
            case keyboard.Key.f3:
                print('removing recoil')
                removeRecoil()
            case keyboard.Key.f4:
                print('getting grenade')
                addGrenade()
            case keyboard.Key.f5:
                option = input('type "team" or "solo" to include for invincibility: ')
                makeInvulnerable(option)
            case keyboard.Key.f6:
                value = input('type a positive number between 0 and 170 to set the FOV: ')
                changeFOV(value)
            case keyboard.Key.esc:
                print('exiting')
                return False
            case keyboard.Key.enter:
                printInstructions()
            case keyboard.Key.delete:
                clearHacks()
            case _:
                pass
    except: 
        pass 

def printInstructions():
    print("Type corresponding key to choose what you want to have/do:")
    print("f1. infinite ammo")
    print("f2. increased health")
    print("f3. remove recoil")
    print('f4. add grenade to inventory')
    print('f5. become invulnerable')
    print('f6. change FOV')
    print('esc: exit program')
    print('del: clear hacks')
    print('enter: reprint instructions')


def main():
    printInstructions() 

    listener = KeyListener(on_press=on_press)
    listener.start()
    listener.join()


if __name__ == "__main__":
    print("starting hack")
    try:
        main()
    finally:
        #free malloced memory and write back old instructions (if changed)
        process.free(alloc_mem_addr) 
        clearHacks()
        
