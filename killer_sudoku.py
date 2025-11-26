import time
import sys

class KillerSudokuSolver:
    def __init__(self, cages):
        # 初始化棋盘和数据结构
        self.board          = [[0] * 9 for _ in range(9)]
        self.cage_index     = [[-1] * 9 for _ in range(9)]  # 记录每个格子所属笼子的ID
        self.cages          = cages
        self.num_cages      = len(cages)
        self.cage_total     = [0] * self.num_cages          # 每个笼子的目标和
        self.cage_current   = [0] * self.num_cages          # 每个笼子当前已填数字之和
        self.cage_remaining = [0] * self.num_cages          # 每个笼子剩余未填格子数
        self.cage_digits    = [[False] * 10 for _ in range(self.num_cages)]  # 记录每个笼子中数字是否已使用
        
        # 初始化行、列、九宫格的数字使用情况
        self.row_used = [[False] * 10 for _ in range(9)]
        self.col_used = [[False] * 10 for _ in range(9)]
        self.box_used = [[False] * 10 for _ in range(9)]
        
        # 根据cages输入填充数据结构
        for cage_id, (cells, total) in enumerate(cages):
            self.cage_total[cage_id] = total
            self.cage_remaining[cage_id] = len(cells)
            for cell_index in cells:
                r = cell_index // 9
                c = cell_index % 9
                self.cage_index[r][c] = cage_id
        
        # 初始化显示状态
        self.last_board = [[' '] * 9 for _ in range(9)]
        self.displayed = False
    
    def display_board(self, row=None, col=None, action=""):
        """显示当前棋盘状态"""
        if not self.displayed:
            # 首次显示，打印完整的棋盘框架
            print("\n" + "="*50)
            print(f"杀手数独求解器 | 当前操作: {action}")
            print("="*50)
            
            # 打印列号
            col_header = "   "
            for c in range(9):
                col_header += f" {c+1}   " if c % 3 == 2 else f" {c+1}  "
            print(col_header)
            
            # 打印顶部边框
            print("  +" + "---+---+----+" * 3)
            self.displayed = True
        else:
            # 非首次显示，回到棋盘顶部
            sys.stdout.write("\033[{}A".format(18))  # 向上移动18行
        
        # 打印棋盘内容
        for r in range(9):
            # 行号
            print(f"{r+1} |", end="")
            
            for c in range(9):
                # 每3列添加分隔线
                if c % 3 == 0 and c > 0:
                    print("|", end="")
                
                # 获取当前格子的值和上次显示的值
                cage_id = self.cage_index[r][c]
                value = self.board[r][c]
                last_value = self.last_board[r][c]
                no_number_yet = False
                
                # 确定显示内容和颜色
                if r == row and c == col:
                    # 当前操作的格子
                    display_value = f"\033[93m{value if value != 0 else '.'}\033[0m"  # 黄色
                elif value != 0:
                    # 已填数字的格子
                    display_value = f"\033[92m{value}\033[0m"  # 绿色
                else:
                    # 未填数字的格子
                    display_value = f"\033[90m{cage_id}\033[0m" if cage_id != -1 else '.'  # 灰色
                    no_number_yet = True
                
                # 只在值变化时更新显示
                if str(value) != last_value:
                    self.last_board[r][c] = str(value) if value != 0 else ' '
                    # 固定宽度输出
                    same_width_value = f" {display_value} " if no_number_yet and cage_id > 9 else f" {display_value}  "
                    sys.stdout.write(same_width_value)
                else:
                    # 固定宽度输出
                    same_width_value = f" {display_value} " if no_number_yet and cage_id > 9 else f" {display_value}  "
                    sys.stdout.write(same_width_value)
            
            print("|")
            
            # 每3行添加分隔线
            if r % 3 == 2 and r < 8:
                print("  +" + "---+---+----+" * 3)
            else:
                print("  +" + "---+---+----+" * 3)
        
        sys.stdout.flush()
    
    def solve(self, visualization=True):
        """解决杀手数独问题"""
        # 开始求解
        if visualization:
            self.display_board(action="开始求解...")
            time.sleep(1)
        
        # 回溯求解函数
        def backtrack(row, col):
            if row == 9:
                if visualization:
                    self.display_board(action="求解完成！")
                return True  # 所有格子已填满，找到解
            
            next_row = row + (col + 1) // 9
            next_col = (col + 1) % 9
            
            if self.board[row][col] != 0:
                return backtrack(next_row, next_col)  # 跳过已填格子
            
            cage_id = self.cage_index[row][col]
            box_idx = (row // 3) * 3 + col // 3  # 计算九宫格索引
            
            for num in range(1, 10):
                if visualization:
                    self.display_board(row, col, f"尝试 {num}")
                
                # 检查行、列、九宫格是否冲突
                if self.row_used[row][num] or self.col_used[col][num] or self.box_used[box_idx][num]:
                    continue
                # 检查笼子内数字是否重复
                if self.cage_digits[cage_id][num]:
                    continue
                
                # 备份当前笼子状态
                old_current = self.cage_current[cage_id]
                old_remaining = self.cage_remaining[cage_id]
                
                # 更新笼子状态
                self.cage_current[cage_id] += num
                self.cage_remaining[cage_id] -= 1
                self.cage_digits[cage_id][num] = True
                
                # 检查笼子约束
                current_sum = self.cage_current[cage_id]
                rem = self.cage_remaining[cage_id]
                total_needed = self.cage_total[cage_id]
                valid_cage = True
                
                if current_sum > total_needed:
                    valid_cage = False
                elif rem == 0:
                    if current_sum != total_needed:
                        valid_cage = False
                else:
                    if current_sum + rem * 1 > total_needed:  # 最小可能值超出
                        valid_cage = False
                    elif current_sum + rem * 9 < total_needed:  # 最大可能值不足
                        valid_cage = False
                
                if valid_cage:
                    # 放置数字并更新标记
                    self.board[row][col] = num
                    self.row_used[row][num] = True
                    self.col_used[col][num] = True
                    self.box_used[box_idx][num] = True
                    
                    if visualization:
                        self.display_board(row, col, f"放置 {num}")
                    
                    # 递归填下一个格子
                    if backtrack(next_row, next_col):
                        return True
                    
                    # 回溯：恢复标记
                    self.board[row][col] = 0
                    self.row_used[row][num] = False
                    self.col_used[col][num] = False
                    self.box_used[box_idx][num] = False
                    
                    if visualization:
                        self.display_board(row, col, f"回溯 {num}")
                
                # 恢复笼子状态
                self.cage_current[cage_id] = old_current
                self.cage_remaining[cage_id] = old_remaining
                self.cage_digits[cage_id][num] = False
            
            if visualization:
                self.display_board(row, col, "回溯")
            return False
        
        # 开始求解
        result = backtrack(0, 0)
        return self.board if result else None

    def print_solution(self):
        """打印最终解决方案"""
        print("\n" + "="*50)
        print("杀手数独最终解:")
        print("="*50)
        
        # 打印列号
        col_header = "   "
        for c in range(9):
            col_header += f" {c+1}   " if c % 3 == 2 else f" {c+1}  "
        print(col_header)
        
        # 打印顶部边框
        print("  +" + "---+---+----+" * 3)
        
        for r in range(9):
            # 行号
            print(f"{r+1} |", end="")
            
            for c in range(9):
                # 每3列添加分隔线
                if c % 3 == 0 and c > 0:
                    print("|", end="")
                
                # 获取当前格子的值
                value = self.board[r][c]
                display_value = f"\033[92m{value}\033[0m" if value != 0 else '.'
                print(f" {display_value}  ", end="")
            
            print("|")
            
            # 每3行添加分隔线
            if r % 3 == 2 and r < 8:
                print("  +" + "---+---+----+" * 3)
            else:
                print("  +" + "---+---+----+" * 3)
        
        print("="*50 + "\n")

# 示例用法
if __name__ == "__main__":
    # 示例输入
    # 这里定义了三个不同难度的笼子配置
    cages_1 = [
        ([0,1,2], 19),
        ([3,4,5], 20),
        ([6,7,16], 11),
        ([8,17], 7),
        ([9,10,18,19], 16),
        ([11,12], 15),
        ([13,22], 10),
        ([14,15,23], 14),
        ([20,21,30], 6),
        ([24,33], 13),
        ([25,26], 15),
        ([27,28,36,45], 17),
        ([29,38], 11),
        ([31,32], 11),
        ([34,43], 10),
        ([35,44,52,53], 14),
        ([37,46], 15),
        ([39,40,41], 14),
        ([42,51], 12),
        ([47,56], 9),
        ([48,49], 15),
        ([50,59,60], 6),
        ([54,55], 11),
        ([57,65,66], 18),
        ([58,67], 7),
        ([61,62,70,71], 24),
        ([63,72], 10),
        ([64,73,74], 11),
        ([68,69], 6),
        ([75,76,77], 20),
        ([78,79,80], 18)
    ]
    
    cages_5 = [
        ([0,1,2,9,18], 20),
        ([3,4,5,6,13], 27),
        ([7,16,25,26], 14),
        ([8,17], 16),
        ([10,11,12,19,20,28], 31),
        ([14,15], 8),
        ([21,29,30], 17),
        ([22,31], 3),
        ([23,32], 16),
        ([24,33], 11),
        ([27,36,37,45,54], 28),
        ([34,35,43], 16),
        ([38,39], 5),
        ([40,41,49,50], 26),
        ([42,51,52], 12),
        ([44,53], 10),
        ([46,55], 13),
        ([47,48], 4),
        ([56,57], 15),
        ([58,59,68], 10),
        ([60,61,62,69,70,78], 31),
        ([63,64,65,74], 20),
        ([66,67,75], 16),
        ([71,79,80], 14),
        ([72,73], 10),
        ([76,77], 12)
    ]

    cages_10 = [
        ([0,1,2,3,9], 23),
        ([4,13,22], 12),
        ([5,6,7,8,17], 27),
        ([10,19,20], 13),
        ([11,12,21], 16),
        ([14,15,23], 18),
        ([16,24,25], 17),
        ([18,27], 13),
        ([26,35], 9),
        ([28,29], 13),
        ([30,31,32,39,40,41], 27),
        ([33,34], 4),
        ([36,45,54,55], 20),
        ([37,38,46], 16),
        ([42,43,52], 15),
        ([44,53,61,62], 20),
        ([47,48,49,50,51], 35),
        ([56,57,65,66], 19),
        ([58,67,76], 14),
        ([59,60,68,69], 19),
        ([63,64,72,73,74,75], 23),
        ([70,71,77,78,79,80], 32)
    ]
    
    solver = KillerSudokuSolver(cages_5)
    start_time = time.time()
    # 可视化会严重拖慢求解速度（约慢4000倍），建议在调试时开启
    solution = solver.solve(visualization=False)
    end_time = time.time()
    
    if solution:
        solver.print_solution()
        print(f"求解时间: {end_time - start_time:.4f}秒")
    else:
        print("未找到解决方案！")
