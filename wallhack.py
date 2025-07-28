# Version: 1.3.0.2

import sys
import pyMeow as pm

try:
    proc = pm.open_process("ac_client.exe")
    base_address = pm.get_module(proc, "ac_client.exe")["base"]
except:
    print('wtf')

class address:
    num_players = base_address + 0x18AC0C
    player_count = pm.r_int(proc, num_players)
    player_address_ptr = base_address + 0x18AC00
    player_ent_addr = pm.r_byte(proc, player_address_ptr)
    ent_list_ptr = player_address_ptr + 0x4
    view_matrix = base_address + 0x17DFD0

class offsets:
    name = 0x205
    health = 0xEC
    armor = 0xF0
    team = 0x30C
    pos = 0x4
    fpos = 0x28
    auto_fire = 0x204

class colors:
    blue = pm.get_color("blue")
    red = pm.get_color("red")
    black = pm.get_color("black")
    white = pm.get_color("white")

class Entity:
    def __init__(self, addr):
        self.addr = addr
        self.health = pm.r_int(proc, addr + offsets.health)
       
        self.name = pm.r_string(proc, addr + offsets.name)
        self.armor = pm.r_int(proc, addr + offsets.armor)
        self.team = pm.r_int(proc, addr + offsets.team)
        self.color = colors.blue if self.team else colors.red
        self.pos3d = pm.r_vec3(proc, self.addr + offsets.pos)
        self.fpos3d = pm.r_vec3(proc, self.addr + offsets.fpos)
        self.pos2d = self.fpos2d = None
        self.head = self.width = self.center = None

    def wts(self, vm):
        try:
            self.pos2d = pm.world_to_screen(vm, self.pos3d)
            self.fpos2d = pm.world_to_screen(vm, self.fpos3d)
            self.head = self.fpos2d["y"] - self.pos2d["y"]
            self.width = self.head / 2
            self.center = self.width / 2
            return True
        except:
            return False

    def display(self):
        pm.draw_rectangle(
            posX=self.pos2d["x"] - self.center,
            posY=self.pos2d["y"] - self.center / 2,
            width=self.width,
            height=self.head + self.center / 2,
            color=pm.fade_color(self.color, 0.3),
        )
        pm.draw_rectangle_lines(
            posX=self.pos2d["x"] - self.center,
            posY=self.pos2d["y"] - self.center / 2,
            width=self.width,
            height=self.head + self.center / 2,
            color=self.color,
            lineThick=1.2,
        )

    def draw_name(self):
        textSize = pm.measure_text(self.name, 15) / 2
        pm.draw_text(
            text=self.name,
            posX=self.pos2d["x"] - textSize,
            posY=self.pos2d["y"],
            fontSize=15,
            color=colors.white,
        )  
    
    def draw_health(self):
        pm.gui_progress_bar(
            posX=self.pos2d["x"] - self.center,
            posY=self.pos2d["y"] - self.center,
            width=self.width,
            height=self.head / 8,
            textLeft="HP: ",
            textRight=f" {self.health}",
            value=self.health,
            minValue=0,
            maxValue=100,
        )
    
    def draw_snapline(self):
        pm.draw_line(
            startPosX=pm.get_screen_width() // 2,
            startPosY=pm.get_screen_height(),
            endPosX=self.pos2d["x"] - self.center,
            endPosY=self.pos2d["y"] - self.center / 2,
            color=self.color,
            thick=1.2,
        )

def getEntAddrList():
    ent_list_addr = pm.r_int(proc, address.ent_list_ptr)
    ent_list = [pm.r_int(proc, ent_list_addr + i * 0x4) for i in range(1, address.player_count)]
    return ent_list

def main():  
    pm.overlay_init('AssaultCube', fps=144)
    while pm.overlay_loop():
        pm.begin_drawing()
        v_matrix = pm.r_floats(proc, address.view_matrix, 16)
        ent_list = getEntAddrList()
        for addr in ent_list:
            try:
                ent = Entity(addr)
                if ent.wts(v_matrix):
                    ent.display()
                    ent.draw_name()
                    ent.draw_health()
                    ent.draw_snapline()
            except:
                continue
        pm.end_drawing()


if __name__ == "__main__":
    main()