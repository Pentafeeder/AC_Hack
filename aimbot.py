import sys
import pyMeow as pm
import math
from pynput import mouse

try:
    proc = pm.open_process("ac_client.exe")
    base_address = pm.get_module(proc, "ac_client.exe")["base"]
except:
    print('wtf')


class address:
    num_players = base_address + 0x18AC0C
    player_count = pm.r_int(proc, num_players)
    player_address_ptr = base_address + 0x18AC00
    player_ent_addr = pm.r_int(proc, player_address_ptr)
    ent_list_ptr = player_address_ptr + 0x4


class offsets:
    name = 0x205
    health = 0xEC
    armor = 0xF0
    team = 0x30C
    pos = 0x4
    fpos = 0x28
    auto_fire = 0x204
    head_pos_ew = 0x4
    head_pos_z = 0xC
    head_pos_ns = 0x8 
    camera_x = 0x34
    camera_y = 0x38
    is_alive = 0x318


class Entity:
    def __init__(self, addr):
        self.y = pm.r_float(proc, addr + offsets.head_pos_ns)
        self.x = pm.r_float(proc, addr + offsets.head_pos_ew)
        self.z = pm.r_float(proc, addr + offsets.head_pos_z) 
        self.addr = addr

def closestDistance(player, ent_list):
    min_dist = sys.maxsize
    closest_ent = None
    for ent in ent_list:
        delta = [player.x - ent.x, player.y - ent.y, player.z - ent.z]
        distance = math.sqrt(delta[0]**2 + delta[1]**2 + delta[2]**2)
        if (distance < min_dist):
            min_dist = distance
            closest_ent = ent
    
    return closest_ent.addr

def getEntAddrList():
    ent_list_addr = pm.r_int(proc, address.ent_list_ptr)
    ent_list = [pm.r_int(proc, ent_list_addr + i * 0x4) for i in range(1, address.player_count)]
    return ent_list


def aimAndShoot():    
    player_team = pm.r_int(proc, address.player_ent_addr + offsets.team)

    ent_addr_list = getEntAddrList()
    
    
    player = Entity(address.player_ent_addr)
    
    enemy_addresses = []
    
    for addr in ent_addr_list:
        if pm.r_int(proc, addr + offsets.team) != player_team:
            enemy_addresses.append(addr)

   
    ent_list = [Entity(addr) for addr in enemy_addresses]
    closest_ent_addr = closestDistance(player, ent_list)
    closest_ent = list(filter(lambda x: x.addr == closest_ent_addr, ent_list))[0]

    # calc angle
    delta = [-player.x + closest_ent.x, -player.y + closest_ent.y, -player.z + closest_ent.z]
    
    hyp = math.sqrt(delta[0]**2 + delta[1]**2 + delta[2]**2)


    angles = [
        -1 * math.atan2(delta[0], delta[1]) / math.pi * 180.0 + 180.0, #yaw
        math.asin(delta[2] / hyp) * 180.0 / math.pi, #pitch
        0.0
    ]

    # change angles
    pm.w_float(proc, address.player_ent_addr + offsets.camera_x, angles[0])
    pm.w_float(proc, address.player_ent_addr + offsets.camera_y, angles[1])
    

def on_click(x, y, button, pressed):
    if pressed:
        aimAndShoot()



def main():
    listener = mouse.Listener(on_click=on_click)
    listener.start()
    listener.join()

if __name__ == "__main__":
    main()