#------------------------------相关库的导入-----------------------------

import random
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------- 道具名称映射 ----------------------------
PROP_NAME = {
    'A': '力量药水',
    'B': '瞬间治疗药水',
    'C': '盾牌',
    'D': '金苹果',
    'E': '虚弱药水',
    'F': '蜘蛛网',
    'G': '瞬间伤害药水'
}

# ---------------------------- 游戏状态管理类 ----------------------------
class GameState:
    """维护游戏的所有动态数据，并提供执行命令的方法"""
    def __init__(self, log_path='log.txt', team_path='team-list.txt'):
        self.log_path = log_path
        self.team_path = team_path
        self.teams = []           # 每个元素为 [队名, 队长, 队员1, 队员2]
        self.songs = []           # 每个元素为 [床曲, 队长曲, 队员1曲, 队员2曲]
        self.lives = []           # 血量 [床血, 队长血, 队员1血, 队员2血]
        self.effect = []          # 效果倍数 [床, 队长, 队员1, 队员2]
        self.prop_pool = []       # 未发放的道具 [(类型, 条件), ...]
        self.prop = []            # 已发放未使用的道具 [(类型, 队伍索引, 成员索引), ...]
        self.bed_broken = []      # 记录每个队伍的床是否已被击破（用于床破时加血）
        self.joined_teams = set() # 记录已加入游戏的队伍
        self.state = 'start'      # 'choose_songs', 'playing', 'death_race', 'end'
        self.team_count = 0
        self.silenced_teams = []
        self.weakened_members = []
        self._load_from_log()

    def _load_from_log(self):
        """从 log.txt 读取所有命令，重建状态"""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        # 重置状态
        self.teams = []
        self.songs = []
        self.lives = []
        self.effect = []
        self.prop_pool = []
        self.prop = []
        self.bed_broken = []
        self.state = 'start'
        self.team_count = 0
        self.joined_teams.clear()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split('$')
            cmd = parts[0]
            if cmd == 'start':
                self.state = 'choose_songs'
            elif cmd == 'team_join':
                team_idx = int(parts[1])
                with open(self.team_path, 'r', encoding='utf-8') as tf:
                    team_lines = tf.readlines()
                team_info = team_lines[team_idx].strip().split('$')
                self.teams.append(team_info)
                self.songs.append(parts[2:6])   # 床曲, 队长曲, 队员1, 队员2
                # 新规则：床20血，个人曲5血(比赛的初级阶段)
                self.lives.append([20, 5, 5, 5])
                self.effect.append([1, 1, 1, 1])
                self.bed_broken.append(False)
                self.silenced_teams.append(False)
                self.weakened_members.append([False, False, False, False])  # 索引0不用
                self.team_count += 1
                self.joined_teams.add(team_info[0])
            elif cmd == 'teams_complete':
                self.state = 'playing'
            elif cmd == 'attack':
                a_team = int(parts[1])
                a_mem = int(parts[2])
                t_team = int(parts[3])
                t_mem = int(parts[4])
                rating = parts[5]   # 可以是 'FC/AP','V','S','A','B'
                # 伤害映射
                damage_map = {'FC/AP':5, 'V':4, 'S':3, 'A':2, 'B':1}
                base_damage = damage_map.get(rating.upper(), 0)
                times = 1
                if self.effect[a_team][a_mem] % 2 == 0:
                    self.effect[a_team][a_mem] //= 2
                    times = 2
                if self.effect[t_team][t_mem] % 3 == 0:
                    self.effect[t_team][t_mem] //= 3
                    times = 0
                damage = base_damage * times
                self._apply_damage(t_team, t_mem, damage)
            elif cmd == 'death_race':
                self.state = 'death_race'
                for i in range(len(self.lives)):
                    for j in range(4):
                        if self.lives[i][j] > 5:
                            self.lives[i][j] = 5
            elif cmd == 'end':
                self.state = 'end'
            elif cmd == 'prop':
                sub = parts[1]
                if sub == 'spawn':
                    # prop$spawn$条件$类型
                    self.prop_pool.append([parts[3], parts[2]])   # [类型, 条件]
                elif sub == 'give':
                    # prop$give$池索引$队伍$成员
                    idx = int(parts[2])
                    team = int(parts[3])
                    mem = int(parts[4])
                    prop_type = self.prop_pool[idx][0]
                    self.prop.append([prop_type, team, mem])
                    self.prop_pool.pop(idx)
                elif sub == 'use':
                    idx = int(parts[2])
                    p = self.prop[idx]
                    p_type = p[0]
                    if p_type == 'A':
                        self.effect[p[1]][p[2]] *= 2
                        self.prop.pop(idx)
                    elif p_type == 'B':
                        target = int(parts[4])
                        self.lives[p[1]][target] += 8
                        # 限制血量上限
                        if self.state == 'playing':
                            if self.lives[p[1]][0] > 20:
                                self.lives[p[1]][0] = 20
                            if target > 0:
                                max_hp = 10 if self.bed_broken[p[1]] else 5
                                if self.lives[p[1]][target] > max_hp:
                                    self.lives[p[1]][target] = max_hp
                        elif self.state == 'death_race':
                            if self.lives[p[1]][target] > 5:
                                self.lives[p[1]][target] = 5
                        self.prop.pop(idx)
                    elif p_type == 'C':
                        target = int(parts[4])
                        self.effect[p[1]][target] *= 3
                        self.prop.pop(idx)
                    elif p_type == 'D':
                        target = int(parts[4])
                        if self.lives[p[1]][target] < 0:
                            self.lives[p[1]][target] = 5
                            self.prop.pop(idx)
                        else:
                            messagebox.showerror("不能给床或者未被淘汰的队员使用")
                        # 若目标未淘汰，道具使用失败，不弹出
                    elif p_type == 'E':
                        t_team = int(parts[3])
                        t_mem = int(parts[4])
                        new_song = parts[5]
                        self.songs[t_team][t_mem] = new_song
                        self.weakened_members[t_team][t_mem] = True   # 标记虚弱
                        self.prop.pop(idx)
                    elif p_type == 'F':
                        #仅标记该队伍，但是不产生具体限制
                        t_team = int(parts[3])
                        self.silenced_teams[t_team] = True
                        self.prop.pop(idx)
                    elif p_type == 'G':
                        t_team = int(parts[3])
                        t_mem = int(parts[4])
                        damage = 5
                        self._apply_damage(t_team, t_mem, damage)
                        self.prop.pop(idx)

    def _apply_damage(self, team, member, damage):
        """统一处理伤害，包括淘汰/倒地判定及床破事件"""
        self.lives[team][member] -= damage
        # 处理死亡/倒地
        if self.lives[team][member] <= 0:
            if member > 0 and self.lives[team][0] > 0:
                self.lives[team][member] = 5   # 床还在的话立刻复活
            else:
                self.lives[team][member] = -10000   # 床没了的话立刻淘汰
        # 检查床是否被击破（首次）
        if member == 0 and self.lives[team][0] <= 0 and not self.bed_broken[team]:
            self.bed_broken[team] = True
            for m in range(1, 4):
                if self.lives[team][m] > -10000:
                    self.lives[team][m] += 5
                    # 根据当前阶段限制血量上限
                    if self.state == 'death_race':
                        if self.lives[team][m] > 5:
                            self.lives[team][m] = 5
                    else:  # playing阶段
                        if self.lives[team][m] > 10:
                            self.lives[team][m] = 10
        # 如果队伍全员淘汰，减少队伍计数
        if all(hp <= -10000 for hp in self.lives[team]):
            self.team_count -= 1
        if self.team_count <= 1:
            self.state = 'end'

    def _append_command(self, cmd_parts):
        """将命令写入 log.txt"""
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write('$'.join(cmd_parts) + '\n')
        self._load_from_log()   # 重新加载以更新状态

    def team_join(self, team_index, songs_list):
        """加入队伍:team_index, [床曲, 队长曲, 队员1, 队员2]"""
        cmd = ['team_join', str(team_index)] + songs_list
        self._append_command(cmd)

    def start_game(self):
        """正式开始比赛"""
        self._append_command(['teams_complete'])

    def attack(self, attacker_team, attacker_mem, target_team, target_mem, rating):
        """发动攻击,rating 为 'FC/AP','V','S','A','B'"""
        cmd = ['attack', str(attacker_team), str(attacker_mem), str(target_team), str(target_mem), rating]
        self._append_command(cmd)

    def death_race(self):
        """进入决战"""
        self._append_command(['death_race'])

    def end_game(self):
        """强制结束"""
        self._append_command(['end'])

    def prop_spawn(self, condition, prop_type):
        """生成道具"""
        cmd = ['prop', 'spawn', condition, prop_type]
        self._append_command(cmd)

    def prop_give(self, pool_index, team, member):
        """发放道具"""
        cmd = ['prop', 'give', str(pool_index), str(team), str(member)]
        self._append_command(cmd)

    def prop_use(self, prop_index, *args):
        """使用道具,args 根据道具类型不同"""
        cmd = ['prop', 'use', str(prop_index)] + [str(a) for a in args]
        self._append_command(cmd)

# ---------------------------- 主应用程序 ----------------------------
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('比赛控制程序')
        self.geometry('1200x700')
        self.state = GameState()
        
        # 设置样式 - 调大字体
        self.style = ttk.Style()
        self.style.configure('Cards.TFrame', background='#f0f0f0')
        self.style.theme_use('clam')
        self.style.configure('TLabel', font=('微软雅黑', 12))          # 从10改为12
        self.style.configure('TButton', font=('微软雅黑', 12), padding=6)  # 从10改为12
        self.style.configure('Header.TLabel', font=('微软雅黑', 16, 'bold')) # 从14改为16
        self.style.configure('Card.TLabelframe', background='#f0f0f0', relief='solid', borderwidth=1)
        self.style.configure('Green.Horizontal.TProgressbar', background='#2ecc71')
        self.style.configure('Red.Horizontal.TProgressbar', background='#e74c3c')

        # 创建选项卡
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        # 队伍管理页
        self.team_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.team_frame, text='队伍管理')
        self.setup_team_tab()

        # 游戏控制页
        self.game_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.game_frame, text='进行游戏')
        self.setup_game_tab()

        # 重置游戏页
        self.reset_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.reset_frame, text='重置游戏')
        self.setup_reset_tab()

        # 悬停提示工具
        self.tooltip = None

    # ------------------------ 工具方法：悬停提示 ------------------------
    def create_tooltip(self, widget, text):
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 20
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = ttk.Label(self.tooltip, text=text, background="#ffffe0", relief='solid', borderwidth=1)
            label.pack()
        def leave(event):
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    # ------------------------ 队伍管理页 ------------------------
    def setup_team_tab(self):
        # 队伍列表显示
        columns = ('编号', '队名', '队长', '队员1', '队员2')
        self.team_tree = ttk.Treeview(self.team_frame, columns=columns, show='headings')
        for col in columns:
            self.team_tree.heading(col, text=col)
            self.team_tree.column(col, width=120, anchor='center')   # 居中对齐
        self.team_tree.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(self.team_frame, orient='vertical', command=self.team_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.team_tree.configure(yscrollcommand=scrollbar.set)

        # 按钮框架
        btn_frame = ttk.Frame(self.team_frame)
        # 在按钮下方添加颜色注释
        color_note = """以下的道具使用时会对使用者或者被使用者添加颜色注释,道具消耗后会恢复正常:\n
1.盾牌:添加到使用者名字上,棕色；
2.力量药水:添加到使用者名字上,红色；
3.盾牌+力量药水混合:添加到使用者名字上,紫色；
4.虚弱药水:添加到被使用者的歌曲名字上,橙色；
5.蜘蛛网:考虑到禁言操作在群内实现,故不显示颜色,仅在log.txt文件中进行登记。"""
        note_label = ttk.Label(self.team_frame, text=color_note, wraplength=200, justify='left')
        btn_frame.pack(side='top', fill='x', pady=5)
        note_label.pack(side='top', fill='x', padx=10, pady=5)
        #采用网格格式而不是pack()
        ttk.Button(btn_frame, text='添加队伍', command=self.add_team).grid(row=0, column=0, padx=20, pady=5)
        ttk.Button(btn_frame, text='删除队伍', command=self.del_team).grid(row=1, column=0, padx=20, pady=5)
        ttk.Button(btn_frame, text='刷新列表', command=self.refresh_team_list).grid(row=2, column=0, padx=20 ,pady=5)

        self.refresh_team_list()

    def refresh_team_list(self):
        for row in self.team_tree.get_children():
            self.team_tree.delete(row)
        try:
            with open('team-list.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return
        for idx, line in enumerate(lines):
            parts = line.strip().split('$')
            if len(parts) >= 4:
                self.team_tree.insert('', 'end', values=(idx, parts[0], parts[1], parts[2], parts[3]))

    def add_team(self):
        dialog = tk.Toplevel(self)
        dialog.title('添加队伍')
        tk.Label(dialog, text='队伍名:').grid(row=0, column=0, padx=5, pady=5)
        tk.Label(dialog, text='队长昵称:').grid(row=1, column=0, padx=5, pady=5)
        tk.Label(dialog, text='队员1昵称:').grid(row=2, column=0, padx=5, pady=5)
        tk.Label(dialog, text='队员2昵称:').grid(row=3, column=0, padx=5, pady=5)

        entries = []
        for i in range(4):
            e = tk.Entry(dialog)
            e.grid(row=i, column=1, padx=5, pady=5)
            entries.append(e)

        def save():
            data = [e.get() for e in entries]
            if any(not s for s in data):
                messagebox.showerror('错误', '所有字段不能为空')
                return
            try:
                with open('team-list.txt','r', encoding='utf-8') as f:
                    lines = f.readlines()
            except FileNotFoundError:
                lines = []

            lines.append('$'.join(data) + '\n')
            with open('team-list.txt', 'w', encoding='utf-8') as f:
                f.writelines(lines)
            self.refresh_team_list()
            dialog.destroy()

        tk.Button(dialog, text='保存', command=save).grid(row=4, column=0, columnspan=2, pady=10)

    def del_team(self):
        selected = self.team_tree.selection()
        if not selected:
            messagebox.showwarning('警告', '请先选择要删除的队伍')
            return
        item = self.team_tree.item(selected[0])
        idx = item['values'][0]
        if messagebox.askyesno('确认', f'确定删除队伍 {item["values"][1]} 吗？'):
            with open('team-list.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if 0 <= idx < len(lines):
                lines.pop(idx)
                with open('team-list.txt', 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self.refresh_team_list()

    # ------------------------ 游戏控制页 ------------------------
    def setup_game_tab(self):
        # 主容器分为左右两栏
        main_paned = ttk.PanedWindow(self.game_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True)

        # 左侧：队伍卡片区域（带滚动条），设置背景色防止灰色残留
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        canvas = tk.Canvas(left_frame, highlightthickness=0, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=canvas.yview)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.canvas = canvas
        self.scrollbar = scrollbar

        # 右侧：道具信息 + 操作按钮（按钮动态生成）
        right_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(right_frame, weight=1)
        self.right_frame = right_frame
        self.setup_right_panel_static()  # 创建静态的道具列表等
        self.refresh_button_panel()       # 动态创建按钮

        # 定时刷新
        self.after(2000, self.auto_refresh)

    def setup_right_panel_static(self):
        """创建右侧面板中不变的部分：阶段标签、道具列表"""
        # 阶段标签
        self.stage_label = ttk.Label(self.right_frame, text='当前阶段：准备阶段', style='Header.TLabel')
        self.stage_label.pack(pady=10)

        # 道具池 Treeview
        ttk.Label(self.right_frame, text='未获取道具').pack()
        self.pool_tree = ttk.Treeview(self.right_frame, columns=('type','cond'), show='headings', height=4)
        self.pool_tree.heading('type', text='道具')
        self.pool_tree.heading('cond', text='条件')
        self.pool_tree.column('type', width=80)
        self.pool_tree.column('cond', width=150)
        self.pool_tree.pack(fill='x', padx=5, pady=2)

        # 已获取道具 Treeview
        ttk.Label(self.right_frame, text='已获取道具').pack()
        self.prop_tree = ttk.Treeview(self.right_frame, columns=('type','owner'), show='headings', height=4)
        self.prop_tree.heading('type', text='道具')
        self.prop_tree.heading('owner', text='持有者')
        self.prop_tree.pack(fill='x', padx=5, pady=2)

        # 按钮容器（用于动态生成）
        self.button_frame = ttk.Frame(self.right_frame)
        self.button_frame.pack(fill='x', pady=10)
        # 阶段提示标签
        self.stage_tip_label = ttk.Label(self.right_frame, text='', wraplength=500, justify='left')
        self.stage_tip_label.pack(fill='x', padx=5, pady=5)

    def refresh_button_panel(self):
        """根据当前阶段重新创建按钮"""
        # 清除原有按钮
        for widget in self.button_frame.winfo_children():
            widget.destroy()

        # 定义各阶段可用的按钮及对应命令
        stage_buttons = {
            'choose_songs': [
                ('加入队伍', self.join_team),
                ('开始比赛', self.start_game),
                ('撤回操作', self.undo_last_command)
            ],
            'playing': [
                ('发动攻击', self.attack),
                ('道具系统', self.prop_system),
                ('进入决战', self.death_race),
                ('撤回操作', self.undo_last_command)
            ],
            'death_race': [
                ('发动攻击', self.attack),
                ('道具系统', self.prop_system),
                ('强制结束', self.end_game),
                ('撤回操作',self.undo_last_command)
            ],
            'end': [('撤回操作',self.undo_last_command)]   
            # 结束阶段添加一个撤回操作，防止操作失误意外结束比赛
        }

        buttons = stage_buttons.get(self.state.state, [])
        for text, cmd in buttons:
            btn = ttk.Button(self.button_frame, text=text, command=cmd)
            btn.pack(fill='x', pady=2)
            # 可添加悬停提示
            tips = {
                '加入队伍': '准备阶段可用',
                '开始比赛': '准备阶段可用',
                '发动攻击': '比赛/决战阶段可用',
                '道具系统': '比赛/决战阶段可用',
                '进入决战': '比赛阶段可用',
                '强制结束': '决战阶段可用',
                '撤回操作': '撤销上一次操作'
            }
            self.create_tooltip(btn, tips.get(text, ''))

    def auto_refresh(self):
        self.refresh_game_display()
        self.after(10000, self.auto_refresh)

    def refresh_game_display(self):
        """更新游戏界面显示（卡片、道具、阶段、按钮）"""
        # 清空卡片区域
        if hasattr(self, 'cards_frame') and self.cards_frame:
            self.cards_frame.destroy()
        self.cards_frame = tk.Frame(self.canvas, bg='#f0f0f0')
        self.cards_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0,0), window=self.cards_frame, anchor='nw')
        # 更新阶段标签
        state_map = {
            'choose_songs': '准备阶段',
            'playing': '比赛阶段',
            'death_race': '决战阶段',
            'end': '比赛结束'
        }
        self.stage_label.config(text=f'当前阶段：{state_map.get(self.state.state, "未知")}')
        # 更新阶段提示
        if self.state.state in ('start', 'choose_songs'):
            tip = """ 如果此界面没有显示任何按钮,请在“重置游戏”界面框中点击重置游戏并且确认,或者在log.txt文档中手动写入“start$”即可。
床曲的级数范围:15.5-15.9   rks以及对应的选歌级数范围如下
RKS14.00以下:定数16.7-16.9   RKS14.00-14.99:定数16.4-16.6,
RKS15.00-15.49:定数16.0-16.3 RKS15.50-15.99:定数15.5-15.9,
RKS16.00-16.39:定数15.0-15.4 RKS16.40-16.69:定数14.5-14.9,
RKS16.70-16.99:定数14.0-14.4 """
        elif self.state.state == 'playing':
            tip = " 正式比赛阶段中,每队的床血量上限是20,队员血量上限是5,床还在的时候队员可以被攻击扣血,队员被击败自动恢复满血。当床被击破的时候,队员血量上限调整为10,并且自动加5滴血量,此时队员被击败即可视为阵亡。如果不小心操作失误导致比赛意外结束,请点击“撤回操作”按钮"
        elif self.state.state == 'death_race':
            tip = " 死战阶段中,无论什么情况,所有队伍的床血量上限为5,所有队员的血量上限调整为5,如果不小心操作失误导致比赛结束，请点击“撤回操作”按钮。"
        else:
            tip = "如果你不小心操作失误导致了比赛意外结束,请点击“撤回操作”的按钮！"
        self.stage_tip_label.config(text=tip)
        # 更新按钮
        self.refresh_button_panel()

        # 每行最多1个卡片
        max_cols = 1
        for idx, team in enumerate(self.state.teams):
            row = idx // max_cols
            col = idx % max_cols
            card = ttk.LabelFrame(self.cards_frame, text='', style='Card.TLabelframe')
            card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')  # 增加卡片边距

            # 队伍名标签（带禁言颜色）
            team_label = ttk.Label(card, text=f'队伍{idx} {team[0]}', font=('微软雅黑', 14, 'bold'))  # 加大字号
            if self.state.silenced_teams[idx]:
                pass
                #先不做效果显示
                # team_label.config(foreground='purple')
            team_label.grid(row=0, column=0, columnspan=4, sticky='w', padx=10, pady=(5,0))

            # 行偏移
            row_offset = 1

            # 显示床信息
            if self.state.lives[idx][0] > 0:
                bed_hp = self.state.lives[idx][0]
                bed_max = 20 if self.state.state != 'death_race' else 5
                bed_percent = max(0, bed_hp) / bed_max if bed_max > 0 else 0

                # 床血量标签
                ttk.Label(card, text='床血量:').grid(row=row_offset, column=0, sticky='w', padx=(10,0), pady=2)
                # 床血条
                bed_bar = ttk.Progressbar(card, length=100, mode='determinate',
                                        style='Green.Horizontal.TProgressbar')
                bed_bar['value'] = bed_percent * 100
                bed_bar.grid(row=row_offset, column=1, padx=5, pady=2, sticky='ew')
                # 床血量数值
                ttk.Label(card, text=f'{bed_hp}/{bed_max}').grid(row=row_offset, column=2, padx=(5,10), pady=2, sticky='w')
                # 床曲标签
                ttk.Label(card, text=f'床曲: {self.state.songs[idx][0]}').grid(row=row_offset, column=3, padx=(10,10), pady=2, sticky='w')
                row_offset += 1
            else:
                row_offset = 1

            # 显示每个队员
            for m in range(1, 4):
                current_row = row_offset + m - 1
                hp = self.state.lives[idx][m]
                max_hp = 5 if self.state.state == 'death_race' else (10 if self.state.bed_broken[idx] else 5)
                
                # 名字标签（带效果颜色）
                name_label = ttk.Label(card, text=team[m])
                effect_val = self.state.effect[idx][m]
                if effect_val % 6 == 0:
                    name_label.config(foreground='purple')   # 力量+盾牌
                elif effect_val % 2 == 0:
                    name_label.config(foreground='red')     # 力量药水
                elif effect_val % 3 == 0:
                    name_label.config(foreground='brown')    # 盾牌
                name_label.grid(row=current_row, column=0, sticky='w', padx=(10,0), pady=2)
                
                if hp <= -10000:
                    # 淘汰状态：不显示血条，只显示“淘汰”文字
                    ttk.Label(card, text='淘汰').grid(row=current_row, column=1, columnspan=2, sticky='w', padx=5)
                elif hp == 0:
                    ttk.Label(card, text='倒地').grid(row=current_row, column=1, columnspan=2, sticky='w', padx=5)
                else:
                    # 血条
                    bar = ttk.Progressbar(card, length=80, mode='determinate',
                                        style='Red.Horizontal.TProgressbar')
                    bar['value'] = (max(0, hp) / max_hp) * 100 if max_hp > 0 else 0
                    bar.grid(row=current_row, column=1, padx=5, pady=2, sticky='ew')
                    # 血量数值
                    ttk.Label(card, text=f'{hp}/{max_hp}').grid(row=current_row, column=2, padx=(5,10), pady=2, sticky='w')
                
                # 曲名（比赛结束前始终显示，带虚弱颜色）
                song_label = ttk.Label(card, text=f'曲: {self.state.songs[idx][m]}')
                if self.state.weakened_members[idx][m]:
                    song_label.config(foreground='blue')
                song_label.grid(row=current_row, column=3, padx=(10,10), pady=2, sticky='w')
            
            # 设置列权重，使布局合理
            card.columnconfigure(0, weight=0, minsize=100)  # 名字列固定宽度
            card.columnconfigure(1, weight=1)               # 血条列可扩展
            card.columnconfigure(2, weight=0, minsize=40)   # 血量数值列固定
            card.columnconfigure(3, weight=2)               # 曲名列给更多空间

        # 配置网格权重
        for i in range(max_cols):
            self.cards_frame.columnconfigure(i, weight=1)

        # 更新道具树
        self.pool_tree.delete(*self.pool_tree.get_children())
        for idx, (ptype, cond) in enumerate(self.state.prop_pool):
            self.pool_tree.insert('', 'end', values=(PROP_NAME[ptype], cond))

        self.prop_tree.delete(*self.prop_tree.get_children())
        for idx, (ptype, team, mem) in enumerate(self.state.prop):
            owner = self.state.teams[team][mem] if team < len(self.state.teams) else '未知'
            self.prop_tree.insert('', 'end', values=(PROP_NAME[ptype], owner))

    # ------------------------ 各种操作对话框 ------------------------
    def join_team(self):
        if self.state.state != 'choose_songs':
            messagebox.showwarning('警告', '只能在准备阶段加入队伍')
            return
        try:
            with open('team-list.txt', 'r', encoding='utf-8') as f:
                teams = [line.strip().split('$') for line in f if line.strip()]
        except FileNotFoundError:
            messagebox.showerror('错误', 'team-list.txt 不存在')
            return

        if not teams:
            messagebox.showwarning('警告', '没有已注册的队伍')
            return

        # 过滤出未加入的队伍，保留原始索引和队伍信息
        available_teams = []
        for idx, team_info in enumerate(teams):
            team_name = team_info[0]
            if team_name not in self.state.joined_teams:
                available_teams.append((idx, team_info))

        if not available_teams:
            messagebox.showwarning('警告', '所有队伍都已加入比赛')
            return

        dialog = tk.Toplevel(self)
        dialog.title('加入队伍')

        tk.Label(dialog, text='选择队伍:').grid(row=0, column=0, padx=5, pady=5)
        team_var = tk.StringVar()
        # 显示选项为 "原始索引:队名"
        team_combo = ttk.Combobox(dialog, textvariable=team_var,
                                values=[f'{idx}:{info[0]}' for idx, info in available_teams])
        team_combo.grid(row=0, column=1, padx=5, pady=5)
        team_combo.current(0)

        # 歌曲输入部分（保持不变）
        tk.Label(dialog, text='床曲:').grid(row=1, column=0, padx=5, pady=5)
        bed_song = tk.Entry(dialog)
        bed_song.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(dialog, text='队长曲:').grid(row=2, column=0, padx=5, pady=5)
        leader_song = tk.Entry(dialog)
        leader_song.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(dialog, text='队员1曲:').grid(row=3, column=0, padx=5, pady=5)
        mem1_song = tk.Entry(dialog)
        mem1_song.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(dialog, text='队员2曲:').grid(row=4, column=0, padx=5, pady=5)
        mem2_song = tk.Entry(dialog)
        mem2_song.grid(row=4, column=1, padx=5, pady=5)

        def do_join():
            idx_str = team_var.get().split(':')[0]
            if not idx_str.isdigit():
                messagebox.showerror('错误', '请选择队伍')
                return
            original_idx = int(idx_str)  # 原始索引
            team_name = team_var.get().split(':')[1]  # 队名

            songs = [bed_song.get(), leader_song.get(), mem1_song.get(), mem2_song.get()]
            if any(not s for s in songs):
                messagebox.showerror('错误', '所有歌曲不能为空')
                return

            # 执行加入队伍命令
            self.state.team_join(original_idx, songs)

            self.refresh_game_display()
            dialog.destroy()

        tk.Button(dialog, text='确认', command=do_join).grid(row=5, column=0, columnspan=2, pady=10)
    def start_game(self):
        if self.state.state != 'choose_songs':
            messagebox.showwarning('警告', '只能在准备阶段开始比赛')
            return
        self.state.start_game()
        self.refresh_game_display()

    def attack(self):
        if self.state.state not in ('playing', 'death_race'):
            messagebox.showwarning('警告', '只能在比赛或决战阶段发动攻击')
            return
        if len(self.state.teams) == 0:
            messagebox.showwarning('警告', '没有队伍')
            return
        dialog = tk.Toplevel(self)
        dialog.title('发动攻击')
        dialog.grab_set()   # 模态

        # 攻击者队伍选择
        tk.Label(dialog, text='攻击者队伍:').grid(row=0, column=0, padx=5, pady=5)
        attacker_team_var = tk.StringVar()
        attacker_team_combo = ttk.Combobox(dialog, textvariable=attacker_team_var,
                                           values=[f'{i}:{t[0]}' for i,t in enumerate(self.state.teams)])
        attacker_team_combo.grid(row=0, column=1, padx=5, pady=5)
        attacker_team_combo.current(0)

        # 攻击者成员按钮
        tk.Label(dialog, text='攻击者成员:').grid(row=1, column=0, padx=5, pady=5)
        attacker_mem_frame = ttk.Frame(dialog)
        attacker_mem_frame.grid(row=1, column=1, padx=5, pady=5)
        attacker_mem_var = tk.IntVar(value=1)

        def update_attacker_buttons(*args):
            # 根据选择的队伍更新成员名字
            try:
                team_idx = int(attacker_team_var.get().split(':')[0])
                team = self.state.teams[team_idx]
            except:
                return
            for widget in attacker_mem_frame.winfo_children():
                widget.destroy()
            for m in range(1, 4):
                name = team[m]
                rb = tk.Radiobutton(attacker_mem_frame, text=name, variable=attacker_mem_var, value=m)
                rb.pack(side='left')
        attacker_team_var.trace('w', update_attacker_buttons)
        update_attacker_buttons()

        # 目标队伍选择
        tk.Label(dialog, text='目标队伍:').grid(row=2, column=0, padx=5, pady=5)
        target_team_var = tk.StringVar()
        target_team_combo = ttk.Combobox(dialog, textvariable=target_team_var,
                                         values=[f'{i}:{t[0]}' for i,t in enumerate(self.state.teams)])
        target_team_combo.grid(row=2, column=1, padx=5, pady=5)
        target_team_combo.current(0)

        # 目标成员按钮（包括床）
        tk.Label(dialog, text='目标成员:').grid(row=3, column=0, padx=5, pady=5)
        target_mem_frame = ttk.Frame(dialog)
        target_mem_frame.grid(row=3, column=1, padx=5, pady=5)
        target_mem_var = tk.IntVar(value=0)

        def update_target_buttons(*args):
            try:
                team_idx = int(target_team_var.get().split(':')[0])
                team = self.state.teams[team_idx]
            except:
                return
            for widget in target_mem_frame.winfo_children():
                widget.destroy()
            # 床选项
            rb_bed = tk.Radiobutton(target_mem_frame, text='床', variable=target_mem_var, value=0)
            rb_bed.pack(side='left')
            for m in range(1, 4):
                name = team[m]
                rb = tk.Radiobutton(target_mem_frame, text=name, variable=target_mem_var, value=m)
                rb.pack(side='left')
        target_team_var.trace('w', update_target_buttons)
        update_target_buttons()

        # 评级单选
        tk.Label(dialog, text='评级:').grid(row=4, column=0, padx=5, pady=5)
        rating_var = tk.StringVar(value='V')
        rating_frame = ttk.Frame(dialog)
        rating_frame.grid(row=4, column=1, padx=5, pady=5)
        for rating in ('FC/AP', 'V', 'S', 'A', 'B'):
            rb = tk.Radiobutton(rating_frame, text=rating, variable=rating_var, value=rating)
            rb.pack(side='left')

        def do_attack():
            try:
                a_team = int(attacker_team_var.get().split(':')[0])
                a_mem = attacker_mem_var.get()
                t_team = int(target_team_var.get().split(':')[0])
                t_mem = target_mem_var.get()
                rating = rating_var.get()
            except:
                messagebox.showerror('错误', '请完整选择')
            #死亡判定
            if self.state.lives[a_team][a_mem] <= -10000:
                messagebox.showerror('错误', '攻击者已被淘汰，无法攻击')
                return
            #攻击己方人员判定
            if a_team == t_team:
                messagebox.showerror('错误', '不能攻击己方队伍')
                return

            self.state.attack(a_team, a_mem, t_team, t_mem, rating)
            self.refresh_game_display()
            dialog.destroy()

        tk.Button(dialog, text='攻击', command=do_attack).grid(row=5, column=0, columnspan=2, pady=10)

    def prop_system(self):
        if self.state.state not in ('playing', 'death_race'):
            messagebox.showwarning('警告', '只能在比赛或决战阶段使用道具系统')
            return
        dialog = tk.Toplevel(self)
        dialog.geometry('300x200')          # 设置固定宽高
        dialog.title('道具系统')
        tk.Label(dialog, text='请选择操作：').pack(pady=5)
        tk.Button(dialog, text='生成道具', command=lambda: [dialog.destroy(), self.prop_spawn()]).pack(fill='x', padx=20, pady=2)
        tk.Button(dialog, text='发放道具', command=lambda: [dialog.destroy(), self.prop_give()]).pack(fill='x', padx=20, pady=2)
        tk.Button(dialog, text='使用道具', command=lambda: [dialog.destroy(), self.prop_use()]).pack(fill='x', padx=20, pady=2)

    def prop_spawn(self):
        try:
            with open('events.txt', 'r', encoding='utf-8') as f:
                events = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            messagebox.showerror('错误', 'events.txt 不存在')
            return
        if not events:
            messagebox.showwarning('警告', 'events.txt 中没有条件')
            return

        condition = random.choice(events)
        dialog = tk.Toplevel(self)
        dialog.title('生成道具')
        tk.Label(dialog, text=f'抽选到的条件：{condition}').pack(pady=5)
        tk.Label(dialog, text='选择道具类型：').pack()
        var = tk.StringVar()
        desc = {
                'A': '力量药水：下次攻击伤害翻倍',
                'B': '瞬间治疗药水:回复8点血量',
                'C': '盾牌：免疫下一次伤害',
                'D': '金苹果:复活已淘汰队友(5血)',
                'E': '虚弱药水：更改目标个人曲',
                'F': '蜘蛛网:禁言目标队伍5分钟',
                'G': '瞬间伤害药水:造成5点伤害'
            }
        for key, name in PROP_NAME.items():
            rb = tk.Radiobutton(dialog, text=name, variable=var, value=key)
            rb.pack(anchor='w')
            self.create_tooltip(rb, desc[key])
        def confirm():
            if not var.get():
                messagebox.showerror('错误', '请选择道具类型')
                return
            self.state.prop_spawn(condition, var.get())
            self.refresh_game_display()
            dialog.destroy()
        tk.Button(dialog, text='生成', command=confirm).pack(pady=10)

    def prop_give(self):
        if not self.state.prop_pool:
            messagebox.showwarning('警告', '没有可发放的道具')
            return
        dialog = tk.Toplevel(self)
        dialog.title('发放道具')
        dialog.grab_set()

        tk.Label(dialog, text='选择道具:').grid(row=0, column=0, padx=5, pady=5)
        pool_var = tk.StringVar()
        pool_combo = ttk.Combobox(dialog, textvariable=pool_var,
                                  values=[f'{i}:{PROP_NAME[p[0]]} 条件:{p[1]}' for i,p in enumerate(self.state.prop_pool)])
        pool_combo.grid(row=0, column=1, padx=5, pady=5)
        pool_combo.current(0)

        tk.Label(dialog, text='目标队伍:').grid(row=1, column=0, padx=5, pady=5)
        team_var = tk.StringVar()
        team_combo = ttk.Combobox(dialog, textvariable=team_var,
                                  values=[f'{i}:{t[0]}' for i,t in enumerate(self.state.teams)])
        team_combo.grid(row=1, column=1, padx=5, pady=5)
        if self.state.teams:
            team_combo.current(0)

        # 目标成员按钮
        tk.Label(dialog, text='目标成员:').grid(row=2, column=0, padx=5, pady=5)
        member_frame = ttk.Frame(dialog)
        member_frame.grid(row=2, column=1, padx=5, pady=5)
        member_var = tk.IntVar(value=1)

        def update_member_buttons(*args):
            try:
                team_idx = int(team_var.get().split(':')[0])
                team = self.state.teams[team_idx]
            except:
                return
            for widget in member_frame.winfo_children():
                widget.destroy()
            for m in range(1, 4):
                name = team[m]
                rb = tk.Radiobutton(member_frame, text=name, variable=member_var, value=m)
                rb.pack(side='left')
        team_var.trace('w', update_member_buttons)
        update_member_buttons()

        def confirm():
            try:
                pool_idx = int(pool_var.get().split(':')[0])
                team_idx = int(team_var.get().split(':')[0])
                mem = member_var.get()
            except:
                messagebox.showerror('错误', '输入无效')
                return
            # 检查目标是否被淘汰
            if self.state.lives[team_idx][mem] <= -10000:
                messagebox.showerror('错误', '目标已被淘汰，无法发放道具')
                return
            self.state.prop_give(pool_idx, team_idx, mem)
            self.refresh_game_display()
            dialog.destroy()
        tk.Button(dialog, text='发放', command=confirm).grid(row=3, column=0, columnspan=2, pady=10)

    def prop_use(self):
        if not self.state.prop:
            messagebox.showwarning('警告', '没有可使用的道具')
            return
        dialog = tk.Toplevel(self)
        dialog.title('使用道具')
        dialog.grab_set()

        tk.Label(dialog, text='选择道具：').grid(row=0, column=0, padx=5, pady=5)
        prop_var = tk.StringVar()
        prop_combo = ttk.Combobox(dialog, textvariable=prop_var,
                                  values=[f'{i}:{PROP_NAME[p[0]]} 持有者:{self.state.teams[p[1]][p[2]]}'
                                          for i,p in enumerate(self.state.prop)])
        prop_combo.grid(row=0, column=1, padx=5, pady=5)
        prop_combo.current(0)

        # 额外参数区域
        extra_frame = ttk.Frame(dialog)
        extra_frame.grid(row=1, column=0, columnspan=2, pady=5)

        def on_prop_select(*args):
            # 清除之前的内容
            for widget in extra_frame.winfo_children():
                widget.destroy()
            try:
                idx = int(prop_var.get().split(':')[0])
                ptype = self.state.prop[idx][0]
            except:
                return

            if ptype == 'B':
                owner_team = self.state.prop[idx][1]  # 持有者队伍
                team = self.state.teams[owner_team]
                tk.Label(extra_frame, text='目标成员:').pack()
                member_frame = ttk.Frame(extra_frame)
                member_frame.pack()
                member_var = tk.IntVar(value=0)
                # 床选项
                rb_bed = tk.Radiobutton(member_frame, text='床', variable=member_var, value=0)
                rb_bed.pack(side='left')
                for m in range(1, 4):
                    name = team[m]
                    rb = tk.Radiobutton(member_frame, text=name, variable=member_var, value=m)
                    rb.pack(side='left')
                extra_frame.vars = (owner_team, member_var)  # 存储队伍和成员变量
            elif ptype == 'C':
                owner_team = self.state.prop[idx][1]          # 持有者队伍索引
                team = self.state.teams[owner_team]           # 持有者队伍信息
                tk.Label(extra_frame, text='目标成员:').pack()
                member_frame = ttk.Frame(extra_frame)
                member_frame.pack()
                member_var = tk.IntVar(value=0)                # 默认选床
                # 床选项
                rb_bed = tk.Radiobutton(member_frame, text='床', variable=member_var, value=0)
                rb_bed.pack(side='left')
                for m in range(1, 4):
                    name = team[m]
                    rb = tk.Radiobutton(member_frame, text=name, variable=member_var, value=m)
                    rb.pack(side='left')
                extra_frame.vars = (owner_team, member_var)    # 存储持有者队伍和成员变量
            elif ptype == 'D':
                owner_team = self.state.prop[idx][1]
                team = self.state.teams[owner_team]
                tk.Label(extra_frame, text='目标成员:').pack()
                member_frame = ttk.Frame(extra_frame)
                member_frame.pack()
                member_var = tk.IntVar(value=1)
                for m in range(1, 4):
                    name = team[m]
                    rb = tk.Radiobutton(member_frame, text=name, variable=member_var, value=m)
                    rb.pack(side='left')
                extra_frame.vars = (owner_team, member_var)

            elif ptype == 'E':
                tk.Label(extra_frame, text='目标队伍:').pack()
                team_var = tk.StringVar()
                team_combo = ttk.Combobox(extra_frame, textvariable=team_var,
                                          values=[f'{i}:{t[0]}' for i,t in enumerate(self.state.teams)])
                team_combo.pack()
                if self.state.teams:
                    team_combo.current(0)
                tk.Label(extra_frame, text='目标成员:').pack()
                member_frame = ttk.Frame(extra_frame)
                member_frame.pack()
                member_var = tk.IntVar(value=1)

                def update_member_buttons(*args):
                    try:
                        team_idx = int(team_var.get().split(':')[0])
                        team = self.state.teams[team_idx]
                    except:
                        return
                    for widget in member_frame.winfo_children():
                        widget.destroy()
                    for m in range(1, 4):
                        name = team[m]
                        rb = tk.Radiobutton(member_frame, text=name, variable=member_var, value=m)
                        rb.pack(side='left')
                team_var.trace('w', update_member_buttons)
                update_member_buttons()
                tk.Label(extra_frame, text='新曲名:').pack()
                song_var = tk.Entry(extra_frame)
                song_var.pack()
                extra_frame.vars = (team_var, member_var, song_var)

            elif ptype == 'F':
                tk.Label(extra_frame, text='目标队伍:').pack()
                team_var = tk.StringVar()
                team_combo = ttk.Combobox(extra_frame, textvariable=team_var,
                                          values=[f'{i}:{t[0]}' for i,t in enumerate(self.state.teams)])
                team_combo.pack()
                if self.state.teams:
                    team_combo.current(0)
                extra_frame.var = team_var

            elif ptype == 'G':
                tk.Label(extra_frame, text='目标队伍:').pack()
                team_var = tk.StringVar()
                team_combo = ttk.Combobox(extra_frame, textvariable=team_var,
                                          values=[f'{i}:{t[0]}' for i,t in enumerate(self.state.teams)])
                team_combo.pack()
                if self.state.teams:
                    team_combo.current(0)
                tk.Label(extra_frame, text='目标成员:').pack()
                member_frame = ttk.Frame(extra_frame)
                member_frame.pack()
                member_var = tk.IntVar(value=0)

                def update_member_buttons(*args):
                    try:
                        team_idx = int(team_var.get().split(':')[0])
                        team = self.state.teams[team_idx]
                    except:
                        return
                    for widget in member_frame.winfo_children():
                        widget.destroy()
                    # 床选项
                    rb_bed = tk.Radiobutton(member_frame, text='床', variable=member_var, value=0)
                    rb_bed.pack(side='left')
                    for m in range(1, 4):
                        name = team[m]
                        rb = tk.Radiobutton(member_frame, text=name, variable=member_var, value=m)
                        rb.pack(side='left')
                team_var.trace('w', update_member_buttons)
                update_member_buttons()
                extra_frame.vars = (team_var, member_var)

            else:  # A类型无额外参数
                pass

        prop_var.trace('w', on_prop_select)
        on_prop_select()  # 初始化

        def confirm():
            try:
                idx = int(prop_var.get().split(':')[0])
                ptype = self.state.prop[idx][0]
                args = []
                if ptype == 'A':
                    pass
                elif ptype == 'G':
                    team_str, mem_var = extra_frame.vars
                    t_team = int(team_str.get().split(':')[0])
                    t_mem = mem_var.get()
                    args = [t_team, t_mem]
                elif ptype in ('B','C','D'):
                    owner_team, mem_var = extra_frame.vars
                    t_team = owner_team
                    t_mem = mem_var.get()
                    args = [t_team, t_mem]
                elif ptype == 'E':
                    team_str, mem_var, song = extra_frame.vars
                    t_team = int(team_str.get().split(':')[0])
                    t_mem = mem_var.get()
                    args = [t_team, t_mem, song.get()]
                elif ptype == 'F':
                    t_team = int(extra_frame.var.get().split(':')[0])
                    args = [t_team]
            except Exception as e:
                messagebox.showerror('错误', f'输入无效: {e}')
                return
            # 检查持有者是否被淘汰
            owner_team = self.state.prop[idx][1]
            owner_mem = self.state.prop[idx][2]

            if self.state.lives[owner_team][owner_mem] <= -10000:
                messagebox.showerror('错误', '道具持有者已被淘汰，无法使用')
                return
            
            # 根据道具类型检查目标是否有效
            if ptype in ('B', 'C', 'E', 'G'):
                t_team, t_mem = args[0], args[1]
                if self.state.lives[t_team][t_mem] <= -10000:
                    messagebox.showerror('错误', '目标已被淘汰，无法使用该道具')
                    return
            elif ptype == 'F':
                t_team = args[0]
                if all(self.state.lives[t_team][i] <= -10000 for i in range(4)):
                    messagebox.showerror('错误', '目标队伍已全部淘汰，无法使用')
                    return
            elif ptype == 'D':
                t_team, t_mem = args[0], args[1]
                if self.state.lives[t_team][t_mem] > -10000:
                    messagebox.showerror('错误', '金苹果只能用于已淘汰的队员')
                    return
                
            self.state.prop_use(idx, *args)
            self.refresh_game_display()
            dialog.destroy()

        tk.Button(dialog, text='使用', command=confirm).grid(row=2, column=0, columnspan=2, pady=10)

    def death_race(self):
        if self.state.state != 'playing':
            messagebox.showwarning('警告', '只能在比赛阶段进入决战')
            return
        self.state.death_race()
        self.refresh_game_display()

    def end_game(self):
        if self.state.state != 'death_race':
            messagebox.showwarning('警告', '只能在决战阶段强制结束')
            return
        self.state.end_game()
        self.refresh_game_display()

    def undo_last_command(self):
        """删除 log.txt 中的最后一行命令并刷新"""
        if not messagebox.askyesno('确认', '确定要撤回上一步操作吗？'):
            return
        try:
            with open('log.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            messagebox.showinfo('提示', '没有可撤回的操作')
            return

        if len(lines) <= 1:
            messagebox.showinfo('提示', '没有可撤回的操作')
            return

        # 删除最后一行
        lines = lines[:-1]
        with open('log.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines)

        # 重新加载状态并刷新显示
        self.state._load_from_log()
        self.refresh_game_display()
        messagebox.showinfo('完成', '已撤回上一步操作')

    # ------------------------ 重置游戏页 ------------------------
    def setup_reset_tab(self):
        ttk.Label(self.reset_frame, text='警告:这将清除所有游戏记录！', font=('微软雅黑', 12)).pack(pady=20)
        ttk.Button(self.reset_frame, text='重置游戏', command=self.reset_game).pack()
        # ---------- 制作组信息文本框 ----------
        info_frame = ttk.LabelFrame(self.reset_frame, text='制作组信息', padding=10)
        info_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # 创建文本框，并添加滚动条
        text_frame = ttk.Frame(info_frame)
        text_frame.pack(fill='both', expand=True)
        
        # Text 组件参数说明：
        # height    : 文本框显示的行数（默认10）
        # width     : 文本框显示的字符宽度（默认40）
        # wrap      : 换行方式，'word' 按单词换行，'char' 按字符换行，'none' 不自动换行
        # font      : 字体，可指定 (字体名, 大小, 样式)
        # background: 背景颜色
        # foreground: 文字颜色
        # state     : 'normal' 可编辑，'disabled' 只读
        self.info_text = tk.Text(
            text_frame,
            height=10,           # 10行高
            width=60,            # 60字符宽
            wrap='word',         # 按单词换行
            font=('微软雅黑',14),
            background='#f9f9f9',
            foreground='#333333',
            state='normal'       # 只读
        )
        self.info_text.pack(side='left', fill='both', expand=True)
        
        # 垂直滚动条
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.info_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        # 可预先填入示例内容（用户可自行修改）
        sample_text = """
    -1.程序制作组:
    程序总监:slowmen
    逻辑框架:slowmen
    界面设计:Sulfurfish,deepseek(AI)
    程序测试:slowmen,Sulfurfish
    -2.程序内测组:郴州市一中非日常音游社策划组
    内测成员(顺序不分先后):
        kiko                 headphoneline
        幻冰cube             逐月nameless
        Project_Ekei         夏浪
    联系我们:bilibili上搜索“硫鱼君说Sulfurfish”视频发布者后私信即可
    版本:v2.0.0
    日期:2025-03-14"""
        self.info_text.insert('1.0', sample_text)
        self.info_text.config(state='disabled')
    def reset_game(self):
        if messagebox.askyesno('确认', '确定要重置游戏吗?'):
            with open('log.txt', 'w', encoding='utf-8') as f:
                f.write('start$\n')          # 写入启动命令，使状态变为 choose_songs
            self.state.silenced_teams.clear()
            self.state.weakened_members.clear()
            self.state._load_from_log()
            self.refresh_game_display()
            self.state._load_from_log()
            self.refresh_game_display()
            canvas = self.cards_frame.master
            canvas.config(bg='#f0f0f0')
            self.cards_frame.config(bg='#f0f0f0')
            canvas.update_idletasks()
            messagebox.showinfo('完成', '游戏已重置，现在可以正常操作。')

# ----------------------------启动----------------------------
if __name__ == '__main__':
    app = Application()
    app.mainloop()