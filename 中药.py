import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
from pypinyin import lazy_pinyin
import ctypes
import os
import re
import sys
import math
import pickle
import lzma
from datetime import datetime
from decimal import Decimal, getcontext, Inexact, DivisionByZero
from cryptography.fernet import Fernet

# ▼▼▼▼▼ 1. 将密钥硬编码为全局常量 ▼▼▼▼▼
# 运行 install.py 后，用它生成的最终密钥替换下面这一行
SECRET_KEY_CONSTANT = b'_1vbkLjzgM-zAKMYlYZrvPCPfpWIAPu1MAPVzioRHs8='


# ▲▲▲▲▲ 修改结束 ▲▲▲▲▲


def _preload_user_data():
    """
    (V16 - 强制更新 Admin 权限版)
    每次启动时，强制将最新的全套权限赋予 admin 账户，
    确保管理员拥有新功能（如支出统计）的访问权。
    """
    db_file = 'clinic_data.db'
    all_data = {}

    # 1. 加载数据库
    if not os.path.exists(db_file):
        messagebox.showerror("启动错误", "数据库文件丢失！请先运行安装脚本。")
        sys.exit()

    try:
        f = Fernet(SECRET_KEY_CONSTANT)
        import lzma
        with open(db_file, 'rb') as file:
            encrypted_data = file.read()
        decrypted_data = f.decrypt(encrypted_data)
        uncompressed_data = lzma.decompress(decrypted_data)
        all_data = pickle.loads(uncompressed_data)
    except Exception as e:
        messagebox.showerror("致命错误", f"数据库加载失败: {e}")
        sys.exit()

    # 2. 确保账户结构存在
    if 'user_accounts' not in all_data: all_data['user_accounts'] = {}
    user_accounts = all_data['user_accounts']

    # 3. 定义最新的全套权限 (包含支出统计)
    FULL_PERMISSIONS = {
        # 页面访问
        'allow_tab_prescription': True,
        'allow_tab_appointment': True,  # 信息登记
        'allow_tab_expense': True,  # 支出统计 (新增)
        'allow_tab_commission': True,
        'allow_tab_usermanagement': True,

        # 药方按钮
        'allow_btn_presc_save': True, 'allow_btn_presc_history': True,
        'allow_btn_presc_find': True, 'allow_btn_presc_calculator': True,
        'allow_btn_presc_clear': True, 'allow_btn_presc_export': True,

        # 信息登记按钮
        'allow_btn_appt_save': True, 'allow_btn_appt_find': True,
        'allow_btn_appt_delete': True, 'allow_btn_appt_export_excel': True,
        'allow_btn_appt_export_lemon': True, 'allow_btn_appt_clear_fields': True,

        # 支出统计按钮 (新增)
        'allow_btn_exp_save': True, 'allow_btn_exp_delete': True,
        'allow_btn_exp_export': True,

        # 导出选项
        'export_appt_include_amount': True,
        'export_appt_include_commission': True,
    }

    # 4. 强制更新或创建 Admin
    needs_saving = False

    if 'admin' not in user_accounts:
        # 创建新 admin
        print("创建默认管理员...")
        user_accounts['admin'] = {'password': '9665390276121893', 'permissions': FULL_PERMISSIONS.copy()}
        if 'user_data' not in all_data: all_data['user_data'] = {}
        all_data['user_data']['admin'] = {"prescriptions": [], "appointments": [], "expenses": []}
        needs_saving = True
    else:
        # admin 已存在，强制合并新权限
        # 这一步解决了"为什么我admin没权限"的问题
        current_perms = user_accounts['admin'].get('permissions', {})
        # 将缺失的权限补全为 True
        for key, val in FULL_PERMISSIONS.items():
            if key not in current_perms:
                current_perms[key] = val
                needs_saving = True
        user_accounts['admin']['permissions'] = current_perms

    # 5. 保存更改
    if needs_saving:
        _save_preloaded_data(db_file, all_data)

    return all_data
def _save_preloaded_data(db_file, all_data):
    """(密钥硬编码版) 使用内置的密钥进行加密保存。"""
    f = Fernet(SECRET_KEY_CONSTANT)
    try:
        pickled_data = pickle.dumps(all_data, pickle.HIGHEST_PROTOCOL)
        compressed_data = lzma.compress(pickled_data)
        encrypted_data = f.encrypt(compressed_data)

        with open(db_file, 'wb') as file:
            file.write(encrypted_data)
    except Exception as e:
        print(f"加密并保存数据库时出错: {e}")


class LoginWindow:
    """登录窗口类 (V9: 适应无角色权限结构)"""

    def __init__(self, login_data):
        # 不再需要 roles_permissions
        self.user_accounts = login_data.get('users', {})
        self.root = tk.Tk()
        self.root.title("用户登录")
        self.root.geometry("350x180");
        self.root.resizable(False, False)
        screen_width = self.root.winfo_screenwidth();
        screen_height = self.root.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (350 / 2));
        y_cordinate = int((screen_height / 2) - (180 / 2))
        self.root.geometry(f"350x180+{x_cordinate}+{y_cordinate}")
        self.login_result = None
        self._create_widgets();
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        # 界面完全不变
        frame = ttk.Frame(self.root, padding=20);
        frame.pack(expand=True, fill="both");
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="账号:").grid(row=0, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(frame);
        self.username_entry.grid(row=0, column=1, sticky="ew", pady=5)
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus_set())
        ttk.Label(frame, text="密码:").grid(row=1, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(frame, show="*");
        self.password_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.password_entry.bind("<Return>", self._login)
        btn_frame = ttk.Frame(frame);
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0));
        btn_frame.columnconfigure((0, 1), weight=1)
        login_button = ttk.Button(btn_frame, text="登 录", command=self._login);
        login_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        exit_button = ttk.Button(btn_frame, text="退 出", command=self._on_close);
        exit_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.username_entry.focus_set()

    def _login(self, event=None):
        entered_username = self.username_entry.get().lower().strip()
        entered_password = self.password_entry.get()

        user_data = self.user_accounts.get(entered_username)

        if user_data and user_data.get('password') == entered_password:
            # ▼▼▼▼▼ 核心修改：直接从 user_data 获取权限 ▼▼▼▼▼
            permissions = user_data.get('permissions', {})

            # 准备要返回给主程序的完整信息
            self.login_result = {
                'username': entered_username,
                # 角色名现在可以简单地判断是否为管理员
                'role_name': '管理员' if entered_username == 'admin' else '自定义用户',
                'permissions': permissions
            }
            # ▲▲▲▲▲ 修改结束 ▲▲▲▲▲
            self.root.destroy()
        else:
            messagebox.showerror("登录失败", "账号或密码不正确！", parent=self.root)
            self.password_entry.delete(0, tk.END)

    def _on_close(self):
        self.login_result = None;
        self.root.destroy()

    def run(self):
        self.root.mainloop();
        return self.login_result


class SplashScreen:
    """启动画面类"""

    def __init__(self):
        self.splash = tk.Tk()
        self.splash.title("中药计价与预约管理程序")
        self.splash.geometry("400x250")
        self.splash.resizable(False, False)
        self.splash.configure(bg="#2c3e50")

        # 居中显示
        self.splash.geometry("+{}+{}".format(
            (self.splash.winfo_screenwidth() // 2) - 200,
            (self.splash.winfo_screenheight() // 2) - 125
        ))

        # 移除标题栏
        self.splash.overrideredirect(True)

        # 创建界面
        self._create_widgets()

        # 进度值
        self.progress_value = 0

    def _create_widgets(self):
        # 主标题
        title_label = tk.Label(self.splash, text="中药计价与预约管理程序",
                               font=("Microsoft YaHei", 16, "bold"),
                               fg="white", bg="#2c3e50")
        title_label.pack(pady=(30, 10))

        # 版本信息
        version_label = tk.Label(self.splash, text="Version 2.0",
                                 font=("Microsoft YaHei", 10),
                                 fg="#bdc3c7", bg="#2c3e50")
        version_label.pack(pady=5)

        # 加载状态
        self.status_label = tk.Label(self.splash, text="正在启动程序...",
                                     font=("Microsoft YaHei", 10),
                                     fg="#ecf0f1", bg="#2c3e50")
        self.status_label.pack(pady=20)

        # 进度条
        self.progress = ttk.Progressbar(self.splash, length=300, mode='determinate')
        self.progress.pack(pady=10)

        # 底部信息
        footer_label = tk.Label(self.splash, text="请稍候，程序正在加载中...",
                                font=("Microsoft YaHei", 8),
                                fg="#95a5a6", bg="#2c3e50")
        footer_label.pack(side="bottom", pady=10)

    def update_progress(self, value, status_text=""):
        """更新进度条"""
        self.progress_value = value
        self.progress['value'] = value
        if status_text:
            self.status_label.config(text=status_text)
        self.splash.update()

    def close(self):
        """关闭启动画面"""
        self.splash.destroy()


# 文件: your_script.py
# 类: AdvancedFilterDialog

class AdvancedFilterDialog(tk.Toplevel):
    """
    (V5 - 回归方框打勾版)
    1. 使用 ttk.Checkbutton 显示真实的“方框”。
    2. 使用 grid 布局，确保表头和每列数据严格对齐。
    3. 按钮均匀分布。
    """

    def __init__(self, parent, title, data, display_fields):
        super().__init__(parent)
        self.title(title)
        self.geometry("900x600")  # 宽度加宽以容纳表格
        self.transient(parent)
        self.grab_set()

        self.data = data
        self.display_fields = display_fields
        self.result = None
        self.check_vars = {}  # 存储 {item_id: BooleanVar}

        # --- 1. 顶部：快捷按钮区 ---
        self.btn_frame = ttk.LabelFrame(self, text=" 快捷操作 ", padding=5)
        self.btn_frame.pack(fill="x", padx=10, pady=5)
        # 预留按钮列配置
        for i in range(5): self.btn_frame.columnconfigure(i, weight=1)
        self.btn_index = 0

        # --- 2. 中间：滚动区域 (Canvas + Frame) ---
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        # 这里的 inner_frame 是真正存放表格的地方
        self.inner_frame = ttk.Frame(canvas)

        # 绑定滚动
        self.inner_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 绑定鼠标滚轮
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # --- 3. 绘制表头 (Grid Row 0) ---
        # 第一列留给复选框
        ttk.Label(self.inner_frame, text="选择", font=("", 9, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        col_keys = list(self.display_fields.keys())
        for col_idx, key in enumerate(col_keys):
            label = self.display_fields[key]['label']
            # 使用 Label 并在 grid 中对齐
            ttk.Label(self.inner_frame, text=label, font=("", 9, "bold"), foreground="blue").grid(row=0,
                                                                                                  column=col_idx + 1,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky="w")

        # --- 4. 绘制数据行 (Grid Row 1...) ---
        for i, item in enumerate(self.data):
            row_idx = i + 1
            item_id = item['id']

            # 1. 复选框
            var = tk.BooleanVar(value=False)
            self.check_vars[item_id] = var
            cb = ttk.Checkbutton(self.inner_frame, variable=var)
            cb.grid(row=row_idx, column=0, padx=5, pady=2)

            # 2. 数据列
            for col_idx, key in enumerate(col_keys):
                val = str(item.get(key, ''))
                # 限制长度防止撑破屏幕
                if len(val) > 20: val = val[:18] + ".."
                ttk.Label(self.inner_frame, text=val).grid(row=row_idx, column=col_idx + 1, padx=5, pady=2, sticky="w")

        # --- 5. 底部：确认区 ---
        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(fill="x", side="bottom")

        ttk.Button(bottom_frame, text="取消", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="确认导出", command=self._on_confirm).pack(side="right", padx=5)

    def add_custom_selection_button(self, text, filter_function):
        """添加按钮，均匀分布"""
        row = self.btn_index // 5  # 一行放5个
        col = self.btn_index % 5

        def action():
            is_select_action = True
            if "取消" in text: is_select_action = False

            # 如果是"只选XXX"，先全部清空
            if "只选" in text:
                for var in self.check_vars.values(): var.set(False)
                is_select_action = True

            for item in self.data:
                if filter_function(item):
                    self.check_vars[item['id']].set(is_select_action)

        btn = ttk.Button(self.btn_frame, text=text, command=action)
        btn.grid(row=row, column=col, sticky="ew", padx=2, pady=2)
        self.btn_index += 1

    def _on_confirm(self):
        selected_ids = [iid for iid, var in self.check_vars.items() if var.get()]
        self.result = {'selected_ids': selected_ids}
        self.destroy()

    def show(self):
        # 添加基础按钮
        self.add_custom_selection_button("全部勾选", lambda x: True)
        self.add_custom_selection_button("全部取消", lambda x: False)

        self.wait_window()
        return self.result
def create_checkbox_images():
    """在程序启动时，用代码生成复选框所需的图片数据"""
    # 一个空的方框图片
    unchecked_b64 = b'R0lGODlhEAAQAIABAAAAAP///yH5BAEAAAEALAAAAAAQABAAAAIjjI+py7v4In1s367d33w5ZgCEb6aK54SSAmwDAgA7'
    # 一个打勾的方框图片
    checked_b64 = b'R0lGODlhEAAQAMQAAORBFeNBFeVCFuVDFuVBF+ZBFuaFF+aLF+aPF+dBF+hDF+pGF+tHF+xHFuyJFu2LGO2NGfCRIfeVI/iZJ/mfLf+pM//78AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAB8ALAAAAAAQABAAAAVS4CeOZGme55z+3j4B4SFirV5ZkAFQBK7iQLLklpLgA8gJUgqEQ2GjFCBABw5yQE0jIKB2CpTRrCoLw2Y1yYyGhwEwEg0MRwYn6dGAAcEJCAhEAQvIBgYJERIqFBYuFyE7KSMoGAEAOw=='
    return tk.PhotoImage(data=unchecked_b64), tk.PhotoImage(data=checked_b64)
class MedicineApp:
    DB_FILE = 'prescriptions_data.dat'  # 改为二进制压缩格式

    def __init__(self, root, file_path, all_db_data, username, permissions, splash=None, is_admin_view=False):
        """
        (V17 - 最终初始化版)
        包含：
        1. 数据库结构自动迁移 (销售收入 -> 营业登记)。
        2. 支出统计数据初始化。
        3. 界面与权限加载。
        """
        self.root = root
        # 创建复选框图片资源
        self.unchecked_img, self.checked_img = create_checkbox_images()
        self.csv_path = file_path
        self.splash = splash
        self.all_data = all_db_data
        self.username = username
        self.permissions = permissions
        self.is_admin_view = is_admin_view
        self.is_admin = (self.username == 'admin')

        # --- 1. 数据结构完整性检查 ---
        # 确保当前用户有完整的数据键值
        if self.username not in self.all_data['user_data']:
            self.all_data['user_data'][self.username] = {
                "prescriptions": [],
                "appointments": [],
                "sales_revenue": [],  # 保留以防万一，虽然即将迁移
                "expenses": []  # 新增：支出统计
            }

        # 确保 admin 存在 (用于数据共享)
        if 'admin' not in self.all_data['user_data']:
            self.all_data['user_data']['admin'] = {
                "prescriptions": [], "appointments": [], "sales_revenue": [], "expenses": []
            }

        # --- 2. 执行旧数据迁移 ---
        # 这一步会将旧版[销售收入]合并到[营业登记]，并初始化[expenses]
        # 如果 _migrate_legacy_data 不存在，请确保您添加了我在上一个回答里提供的该函数
        migration_occurred = False
        if hasattr(self, '_migrate_legacy_data'):
            migration_occurred = self._migrate_legacy_data()

        # --- 3. 绑定数据引用 ---
        # 指向内存中的列表，方便操作
        user_data_ref = self.all_data['user_data'][self.username]
        self.current_user_prescriptions = user_data_ref['prescriptions']
        self.current_user_appointments = user_data_ref['appointments']

        # 初始化支出列表 (如果迁移脚本没跑或者漏了，这里兜底补上)
        if 'expenses' not in user_data_ref:
            user_data_ref['expenses'] = []
        self.current_user_expenses = user_data_ref['expenses']

        # --- 4. 构建视图列表 (用于显示) ---
        # 默认显示自己的数据
        self.view_prescriptions = list(self.current_user_prescriptions)
        self.view_appointments = list(self.current_user_appointments)

        # 检查全局共享设置
        is_global_sharing_enabled = self.all_data.get('config_data', {}).get('enable_global_data_sharing', False)

        # 如果是管理员，或者开启了共享，则追加其他人的数据
        if self.is_admin:
            for user, content in self.all_data.get('user_data', {}).items():
                if user != 'admin':
                    self.view_prescriptions.extend(content.get('prescriptions', []))
                    self.view_appointments.extend(content.get('appointments', []))
        elif is_global_sharing_enabled:
            # 普通用户开启共享，可以看到 admin 的数据
            admin_data = self.all_data['user_data']['admin']
            self.view_prescriptions.extend(admin_data.get('prescriptions', []))
            self.view_appointments.extend(admin_data.get('appointments', []))

        # --- 5. 设置窗口标题 ---
        if self.is_admin_view:
            self.root.title(f"中药计价与预约管理程序 [管理员视角 - 正在管理: {self.username}]")
        else:
            self.root.title(f"中药计价与预约管理程序 [用户: {self.username}]")

        # --- 6. 初始化变量与配置 ---
        self.logout_request = False

        # 单位换算表
        self.units = {
            '袋': 1, '盒': 1, '瓶': 1, '克': 1, '十克': 10,
            '毫克 (0.001g)': 0.001, '分 (0.3g)': 0.3, '克 (g)': 1,
            '钱 (3g)': 3, '十克 (10g)': 10, '两 (50g)': 50,
            '公两 (100g)': 100, '斤 (500g)': 500, '公斤 (1000g)': 1000
        }
        self.unit_options = [
            '十克', '克', '袋', '盒', '瓶', '钱 (3g)', '分 (0.3g)',
            '两 (50g)', '公两 (100g)', '斤 (500g)', '公斤 (1000g)', '毫克 (0.001g)'
        ]

        # 拼音映射缓存
        self.medicine_pinyin_map = {}
        self.teacher_pinyin_map = {}

        # 药方编辑状态变量
        self.prescription = []
        self.edit_mode_index = None
        self.patient_name_var = tk.StringVar()
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.doses_var = tk.StringVar(value='1')
        self.editing_id = None

        # --- 7. 加载外部配置 (CSV) ---
        sync_messages = self._sync_all_external_configs(file_path)

        # 如果发生了数据库迁移，保存并通知
        if migration_occurred:
            self._save_database()
            sync_messages.append("系统提示：检测到旧版[销售收入]数据，已自动合并至[营业登记]。")

        if sync_messages:
            # 如果有同步信息，弹窗提示
            messagebox.showinfo("系统消息", "\n".join(sync_messages))

        # 生成拼音索引
        self._generate_pinyin_maps()

        # 最后的安全检查
        if not self.all_data['config_data'].get('medicine_data'):
            messagebox.showerror("致命错误", "未能加载药品数据，程序无法启动。")
            self.root.destroy()
            return

        # --- 8. 创建界面 ---
        self._create_menu()
        self.create_widgets()

    def _migrate_legacy_data(self):
        """
        (V1 - 数据库结构迁移脚本)
        1. 检查并初始化 'expenses' 列表。
        2. 将旧的 'sales_revenue' 数据格式化后迁移到 'appointments' 中。
        返回 True 如果发生了任何更改。
        """
        has_changed = False

        # 遍历所有用户数据 (包括 admin 和普通用户)
        for username, user_data in self.all_data.get('user_data', {}).items():

            # --- 任务1: 初始化支出列表 ---
            if 'expenses' not in user_data:
                user_data['expenses'] = []
                has_changed = True

            # --- 任务2: 迁移销售收入 -> 营业登记 ---
            # 检查是否有旧的 sales_revenue 数据
            if 'sales_revenue' in user_data and user_data['sales_revenue']:
                old_sales = user_data['sales_revenue']
                target_list = user_data.get('appointments', [])

                print(f"正在迁移用户 {username} 的 {len(old_sales)} 条销售记录...")

                for sale in old_sales:
                    # 获取旧字段
                    s_date = sale.get('date', '')
                    s_type = sale.get('type', '中药销售')  # 旧数据可能叫"中药销售"或"合作收入"
                    s_summary = sale.get('summary', '')
                    s_payment = sale.get('payment_method', '')
                    s_amount = sale.get('amount', '0')
                    s_id = sale.get('id', datetime.now().isoformat())  # 如果没有ID就生成一个

                    # 推断渠道 (简单推断，详细的由后续保存逻辑处理)
                    s_channel = "银行" if s_payment in ["银行", "收钱吧", "微医"] else "现金"
                    if s_payment not in ["银行", "收钱吧", "微医", "现金", "美团", "大众点评"]:
                        s_channel = "无"

                    # 构建新记录结构 (匹配 appointments 结构)
                    new_record = {
                        "id": s_id,
                        "date": s_date,
                        "hour": "00", "minute": "00",  # 销售记录通常没有具体时间，默认为0点
                        "teacher": "无",  # 销售记录没有医师
                        "customer": s_summary,  # 将摘要挪到客户/摘要栏
                        "type": s_type,
                        "amount": s_amount,
                        "payment": s_payment,
                        "channel": s_channel,
                        "status": "是"  # 默认为已完成
                    }

                    target_list.append(new_record)

                # 迁移完成后，清空旧列表，防止重复迁移
                # 我们保留 key 但清空 list，或者直接 del
                user_data['sales_revenue'] = []
                has_changed = True

        return has_changed

    def _process_lemon_template(self, records, template_file):
        """
        [V15 - 日期修复版]
        1. 修复日期偏差问题：不再传递 datetime 对象，改为直接写入日期字符串。
           (解决 Python->Excel 转换时的时区回拨导致日期少一天的问题)
        2. 保留所有之前的修复（缓存清理、独立进程、收/支前缀）。
        """
        import pythoncom
        import win32com.client as win32
        import os
        import sys
        import shutil
        # 移除 datetime 对象的转换，只用它来校验格式
        from datetime import datetime

        if not records: return 0, None

        template_path = os.path.join(os.getcwd(), template_file)
        if not os.path.exists(template_path): return -1, f"模板文件未找到：\n{template_path}"

        # 1. 清理缓存 (防报错)
        try:
            win32_pkg_path = os.path.abspath(os.path.join(win32.__file__, "..", ".."))
            gen_py_path = os.path.join(win32_pkg_path, "gen_py")
            if os.path.exists(gen_py_path): shutil.rmtree(gen_py_path)
        except:
            pass

        excel = None
        workbook = None
        try:
            pythoncom.CoInitialize()

            # 2. 启动 Excel
            try:
                excel = win32.DispatchEx("Excel.Application")
            except:
                excel = win32.Dispatch("Excel.Application")

            try:
                excel.Visible = False; excel.DisplayAlerts = False
            except:
                pass

            workbook = excel.Workbooks.Open(template_path)
            sheet = workbook.Sheets(1)

            # 3. 扫描标题
            header_map = {}
            col_c_letter, col_h_letter = None, None

            try:
                max_row = min(sheet.UsedRange.Rows.Count + 5, 50)
                max_col = min(sheet.UsedRange.Columns.Count + 5, 50)
            except:
                max_row, max_col = 30, 30

            for i in range(1, max_row):
                temp_map = {}
                for j in range(1, max_col):
                    cell_val = sheet.Cells(i, j).Value
                    if cell_val:
                        cell_str = str(cell_val).strip()
                        temp_map[cell_str] = j
                        if cell_str == "收支类别名称":
                            col_c_letter = chr(ord('A') + j - 1)
                        elif cell_str == "项目":
                            col_h_letter = chr(ord('A') + j - 1)
                if "日期" in temp_map and "摘要" in temp_map:
                    header_map = temp_map
                    break

            if not header_map: raise ValueError("找不到标题行")

            # 4. 写入准备
            xlUp = -4162
            date_col = header_map.get("日期", 1)
            last_row = sheet.Cells(sheet.Rows.Count, date_col).End(xlUp).Row
            start_row = last_row + 1

            code_d_key = next((k for k in header_map if "收支类别编码" in k), None)
            col_d_idx = header_map.get(code_d_key) if code_d_key else None
            code_i_key = next((k for k in header_map if "项目编码" in k), None)
            col_i_idx = header_map.get(code_i_key) if code_i_key else None

            # 5. 写入循环
            for i, record in enumerate(records):
                current_row = start_row + i

                # ▼▼▼ 核心修复：直接获取日期字符串，不要转换成 datetime 对象 ▼▼▼
                # 这样 Excel 接收到的是纯文本 "2023-05-20"，绝对不会因为时区变成立 "2023-05-19"
                date_str = str(record.get('date', '')).strip()

                # 简单校验格式，如果不是日期格式，才尝试修复，否则原样写入
                try:
                    # 仅校验，不转换
                    datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    # 如果格式不对，给个默认当天
                    date_str = datetime.now().strftime('%Y-%m-%d')
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                try:
                    a_val = float(record.get('amount', 0))
                except:
                    a_val = 0.0

                cat_val = record.get('teacher', '')
                if not cat_val.startswith('收-') and not cat_val.startswith('支-'):
                    cat_val = f"收-{cat_val}"

                # 写入
                if "日期" in header_map:
                    cell = sheet.Cells(current_row, header_map["日期"])
                    # 强制设为文本格式或日期格式，直接填字符串
                    cell.NumberFormatLocal = "yyyy-mm-dd"
                    cell.Value = date_str  # <--- 这里直接传字符串

                if "摘要" in header_map: sheet.Cells(current_row, header_map["摘要"]).Value = record.get('customer', '')
                if "收支类别名称" in header_map: sheet.Cells(current_row, header_map["收支类别名称"]).Value = cat_val
                if "往来单位" in header_map: sheet.Cells(current_row, header_map["往来单位"]).Value = record.get(
                    'payment', '')
                if "项目" in header_map: sheet.Cells(current_row, header_map["项目"]).Value = record.get('type', '')

                # 金额分流
                if 'amount' in record and "收入（借方）" in header_map:
                    try:
                        val = float(record['amount'])
                    except:
                        val = 0.0
                    sheet.Cells(current_row, header_map["收入（借方）"]).Value = val

                if 'expense' in record and "支出（贷方）" in header_map:
                    try:
                        val = float(record['expense'])
                    except:
                        val = 0.0
                    sheet.Cells(current_row, header_map["支出（贷方）"]).Value = val

                # 公式
                if col_d_idx and col_c_letter:
                    sheet.Cells(current_row,
                                col_d_idx).Formula = f'=IF(ISERROR(VLOOKUP({col_c_letter}{current_row},收支类别参考表!A:B,2,FALSE)),"",VLOOKUP({col_c_letter}{current_row},收支类别参考表!A:B,2,FALSE))'
                if col_i_idx and col_h_letter:
                    sheet.Cells(current_row,
                                col_i_idx).Formula = f'=IF(ISERROR(VLOOKUP({col_h_letter}{current_row},项目参考表!A:B,2,FALSE)),"",VLOOKUP({col_h_letter}{current_row},项目参考表!A:B,2,FALSE))'

            workbook.Save()
            workbook.Close()
            try:
                excel.Quit()
            except:
                pass
            return len(records), None

        except Exception as e:
            try:
                workbook.Close(False)
            except:
                pass
            try:
                excel.Quit()
            except:
                pass
            return -1, str(e)
        finally:
            pythoncom.CoUninitialize()
    def export_expenses_excel(self):
        """普通Excel导出 (支出)"""
        import pandas as pd
        if not self.current_user_expenses:
            messagebox.showinfo("提示", "没有支出记录。")
            return

        # 弹窗选择
        display_fields = {
            'date': {'label': '日期'},
            'type': {'label': '支出类型'},
            'summary': {'label': '摘要'},
            'amount': {'label': '金额'},
            'payment': {'label': '付款方式'}
        }
        dialog = AdvancedFilterDialog(self.root, "导出支出记录 (Excel)", self.current_user_expenses, display_fields)

        # 添加全选/取消
        dialog.add_custom_selection_button("全部勾选", lambda x: True)
        dialog.add_custom_selection_button("全部取消", lambda x: False)

        result = dialog.show()
        if not result or not result.get('selected_ids'): return

        selected_ids = result['selected_ids']
        target_data = [r for r in self.current_user_expenses if r['id'] in selected_ids]

        try:
            filename = filedialog.asksaveasfilename(title="保存支出记录", defaultextension=".xlsx",
                                                    filetypes=[("Excel", "*.xlsx")])
            if filename:
                df = pd.DataFrame(target_data)
                # 重命名列
                cols_map = {'date': '日期', 'type': '支出类型', 'summary': '摘要', 'amount': '金额',
                            'payment': '付款方式'}
                df = df.rename(columns=cols_map)
                # 只保留需要的列
                df = df[list(cols_map.values())]
                df.to_excel(filename, index=False)
                messagebox.showinfo("成功", f"已导出 {len(target_data)} 条记录。")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def export_expenses_lemon_cloud(self):
        """
        [修正版] 导入柠檬云 (支出版)
        自动在类型前添加 '支-' 前缀，满足财务软件格式要求。
        """
        if not self.current_user_expenses:
            messagebox.showinfo("提示", "没有支出记录。")
            return

        display_fields = {
            'date': {'label': '日期'},
            'type': {'label': '类型'},
            'summary': {'label': '摘要'},
            'amount': {'label': '金额'},
            'payment': {'label': '付款'}
        }

        dialog = AdvancedFilterDialog(self.root, "导出支出至柠檬云 (请勾选)", self.current_user_expenses,
                                      display_fields)
        dialog.add_custom_selection_button("全选 [银行] 支出", lambda x: x.get('payment') == '银行')
        dialog.add_custom_selection_button("全选 [现金] 支出", lambda x: x.get('payment') == '现金')
        dialog.add_custom_selection_button("全部勾选", lambda x: True)

        result = dialog.show()
        if not result or not result.get('selected_ids'): return

        target = [r for r in self.current_user_expenses if r['id'] in result['selected_ids']]

        bank_recs = [r for r in target if r.get('payment') == '银行']
        cash_recs = [r for r in target if r.get('payment') == '现金']

        # 转换函数
        def transform(r):
            # 获取界面上显示的类型 (例如 "水电费")
            raw_type = r.get('type', '')
            # ▼▼▼ 核心修改：手动补全 [支-] 前缀 ▼▼▼
            if not raw_type.startswith("支-"):
                formatted_type = f"支-{raw_type}"
            else:
                formatted_type = raw_type

            return {
                "date": r.get('date'),
                "customer": r.get('summary'),
                "teacher": formatted_type,  # 对应收支类别 (如 "支-水电费")
                "expense": r.get('amount'),  # 放在支出列
                "payment": r.get('payment'),
                "type": "支出"
            }

        msgs = []
        if cash_recs:
            c, e = self._process_lemon_template([transform(r) for r in cash_recs], '现金日记账导入模板.xls')
            if e:
                messagebox.showerror("现金导出错", e)
            else:
                msgs.append(f"现金日记账: 追加 {c} 条支出")

        if bank_recs:
            c, e = self._process_lemon_template([transform(r) for r in bank_recs], '银行日记账导入模板.xls')
            if e:
                messagebox.showerror("银行导出错", e)
            else:
                msgs.append(f"银行日记账: 追加 {c} 条支出")

        if msgs: messagebox.showinfo("完成", "\n".join(msgs))

    def _create_user_and_role_management_widgets(self):
        """
        (V15 - 文案净化版)
        去掉多余的括号备注，保持界面整洁。
        """
        if self.is_admin:
            main_frame = ttk.Frame(self.user_management_frame, padding=10)
            main_frame.pack(fill="both", expand=True)
            main_frame.columnconfigure(1, weight=1)
            main_frame.rowconfigure(0, weight=1)

            # 用户列表
            user_list_frame = ttk.LabelFrame(main_frame, text=" 用户列表 ", padding=10)
            user_list_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))

            cols = ("username",)
            self.user_tree = ttk.Treeview(user_list_frame, columns=cols, show='headings', height=20)
            self.user_tree.heading("username", text="用户名")
            self.user_tree.column("username", width=150, anchor='center')
            self.user_tree.pack(fill="both", expand=True)
            self.user_tree.bind("<<TreeviewSelect>>", self._load_user_for_edit)

            # 编辑区
            edit_notebook = ttk.Notebook(main_frame)
            edit_notebook.grid(row=0, column=1, sticky="nsew")

            # === Tab 1: 账户 ===
            user_tab_frame = ttk.Frame(edit_notebook, padding=(10, 10, 10, 0))
            edit_notebook.add(user_tab_frame, text="账户与权限")
            user_tab_frame.columnconfigure(0, weight=1)
            user_tab_frame.rowconfigure(2, weight=1)

            # A. 信息
            info_frame = ttk.LabelFrame(user_tab_frame, text=" 基本信息 ", padding=10)
            info_frame.grid(row=0, column=0, sticky="ew")
            info_frame.columnconfigure(1, weight=1)

            ttk.Label(info_frame, text="用户名:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.um_username = tk.StringVar()
            self.um_username_entry = ttk.Entry(info_frame, textvariable=self.um_username)
            self.um_username_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

            ttk.Label(info_frame, text="密码:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.um_password = tk.StringVar()
            self.um_password_entry = ttk.Entry(info_frame, textvariable=self.um_password)
            self.um_password_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

            # B. 模板
            template_frame = ttk.LabelFrame(user_tab_frame, text=" 权限模板 ", padding=(10, 5))
            template_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
            template_frame.columnconfigure((0, 1, 2), weight=1)
            ttk.Button(template_frame, text="前台 (全权限)",
                       command=lambda: self._apply_permission_template('reception')).grid(row=0, column=0, sticky="ew",
                                                                                          padx=2)
            ttk.Button(template_frame, text="药剂师 (仅药方)",
                       command=lambda: self._apply_permission_template('pharmacist')).grid(row=0, column=1, sticky="ew",
                                                                                           padx=2)
            ttk.Button(template_frame, text="医师 (仅查看)",
                       command=lambda: self._apply_permission_template('doctor')).grid(row=0, column=2, sticky="ew",
                                                                                       padx=2)

            # C. 详细权限
            perm_notebook_inner = ttk.Notebook(user_tab_frame)
            perm_notebook_inner.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

            self.um_permissions_vars = {}

            # 1. 页面访问
            p_frame1 = ttk.Frame(perm_notebook_inner, padding=10)
            perm_notebook_inner.add(p_frame1, text="页面访问")

            page_perms = {
                'allow_tab_prescription': '访问 [药方管理]',
                'allow_tab_appointment': '访问 [信息登记]',
                'allow_tab_expense': '访问 [支出统计]',
                'allow_tab_commission': '访问 [提成统计]',
                'allow_tab_usermanagement': '访问 [用户管理]'
            }
            r = 0
            for key, text in page_perms.items():
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(p_frame1, text=text, variable=var)
                cb.grid(row=r, column=0, sticky="w", pady=2)
                self.um_permissions_vars[key] = (var, cb)
                r += 1

            # 2. 药方功能
            p_frame2 = ttk.Frame(perm_notebook_inner, padding=10)
            perm_notebook_inner.add(p_frame2, text="药方功能")
            presc_perms = {
                'allow_btn_presc_save': '允许 [保存药方]',
                'allow_btn_presc_history': '允许 [历史记录]',
                'allow_btn_presc_find': '允许 [查找]',
                'allow_btn_presc_calculator': '允许 [计算器]',
                'allow_btn_presc_clear': '允许 [清空]',
                'allow_btn_presc_export': '允许 [导出]'
            }
            r = 0
            for key, text in presc_perms.items():
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(p_frame2, text=text, variable=var)
                cb.grid(row=r // 2, column=r % 2, sticky="w", padx=10, pady=2)
                self.um_permissions_vars[key] = (var, cb)
                r += 1

            # 3. 信息登记功能
            p_frame3 = ttk.Frame(perm_notebook_inner, padding=10)
            perm_notebook_inner.add(p_frame3, text="信息登记")
            appt_perms = {
                'allow_btn_appt_save': '允许 [保存/更新]',
                'allow_btn_appt_find': '允许 [查找]',
                'allow_btn_appt_delete': '允许 [删除]',
                'allow_btn_appt_clear_fields': '允许 [清空]',
                'allow_btn_appt_export_excel': '允许 [导出Excel]',
                'allow_btn_appt_export_lemon': '允许 [导入柠檬云]'
            }
            r = 0
            for key, text in appt_perms.items():
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(p_frame3, text=text, variable=var)
                cb.grid(row=r // 2, column=r % 2, sticky="w", padx=10, pady=2)
                self.um_permissions_vars[key] = (var, cb)
                r += 1

            # 4. 支出统计功能
            p_frame4 = ttk.Frame(perm_notebook_inner, padding=10)
            perm_notebook_inner.add(p_frame4, text="支出统计")
            exp_perms = {
                'allow_btn_exp_save': '允许 [保存/更新]',
                'allow_btn_exp_delete': '允许 [删除]',
                'allow_btn_exp_export': '允许 [导出]'
            }
            r = 0
            for key, text in exp_perms.items():
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(p_frame4, text=text, variable=var)
                cb.grid(row=r, column=0, sticky="w", padx=10, pady=2)
                self.um_permissions_vars[key] = (var, cb)
                r += 1

            # 5. 导出隐私
            p_frame5 = ttk.Frame(perm_notebook_inner, padding=10)
            perm_notebook_inner.add(p_frame5, text="导出隐私")
            export_perms = {
                'export_appt_include_amount': '导出中 [包含金额]',
                'export_appt_include_commission': '导出中 [包含提成]'
            }
            r = 0
            for key, text in export_perms.items():
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(p_frame5, text=text, variable=var)
                cb.grid(row=r, column=0, sticky="w", pady=2)
                self.um_permissions_vars[key] = (var, cb)
                r += 1

            # 底部按钮
            bottom_btn_frame = ttk.Frame(user_tab_frame)
            bottom_btn_frame.grid(row=3, column=0, pady=(15, 0), sticky="ew")
            bottom_btn_frame.columnconfigure(0, weight=1)
            std_btn_frame = ttk.Frame(bottom_btn_frame)
            std_btn_frame.grid(row=0, column=0, sticky="ew")
            std_btn_frame.columnconfigure((0, 1, 2), weight=1)

            ttk.Button(std_btn_frame, text="保存用户", command=self._save_user).grid(row=0, column=0, sticky="ew",
                                                                                     padx=(0, 5))
            ttk.Button(std_btn_frame, text="删除用户", command=self._delete_user).grid(row=0, column=1, sticky="ew",
                                                                                       padx=5)
            ttk.Button(std_btn_frame, text="清空表单 (新建)", command=self._clear_user_fields).grid(row=0, column=2,
                                                                                                    sticky="ew",
                                                                                                    padx=(5, 0))

            self.login_as_button = ttk.Button(bottom_btn_frame, text=">>> 以此身份登录 <<<",
                                              command=self._admin_login_as_user)
            self.login_as_button.grid(row=1, column=0, sticky="ew", pady=(10, 0), ipady=4)

            # === Tab 2: 全局 ===
            global_settings_tab = ttk.Frame(edit_notebook, padding=20)
            edit_notebook.add(global_settings_tab, text="全局设置")

            view_lf = ttk.LabelFrame(global_settings_tab, text="数据共享", padding=15)
            view_lf.pack(fill="x", pady=(0, 20))
            self.global_share_var = tk.BooleanVar(
                value=self.all_data.get('config_data', {}).get('enable_global_data_sharing', False))
            ttk.Checkbutton(view_lf, text="开启共享视图模式 (普通用户可见所有人数据)", variable=self.global_share_var,
                            command=self._save_global_settings).pack(anchor="w")

            sync_lf = ttk.LabelFrame(global_settings_tab, text="数据备份", padding=15)
            sync_lf.pack(fill="x")
            ttk.Button(sync_lf, text="同步所有数据至 Admin", command=self._sync_all_data_to_admin).pack(fill="x",
                                                                                                        ipady=4)

            self._populate_users()

        else:
            # ================= 普通用户视图 =================
            main_frame = ttk.Frame(self.user_management_frame, padding=20)
            main_frame.pack(fill="both", expand=True)

            settings_lf = ttk.LabelFrame(main_frame, text=f" 用户 [{self.username}] 的个人设置 ", padding=15)
            settings_lf.pack(fill="x", pady=10)
            settings_lf.columnconfigure(1, weight=1)

            ttk.Label(settings_lf, text="当前密码:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.ps_current_password = tk.StringVar()
            ttk.Entry(settings_lf, textvariable=self.ps_current_password, show="*").grid(row=0, column=1, sticky="ew",
                                                                                         padx=5, pady=5)

            ttk.Label(settings_lf, text="新密码 (留空则不改):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.ps_new_password = tk.StringVar()
            ttk.Entry(settings_lf, textvariable=self.ps_new_password, show="*").grid(row=1, column=1, sticky="ew",
                                                                                     padx=5, pady=5)

            ttk.Label(settings_lf, text="确认新密码:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
            self.ps_confirm_password = tk.StringVar()
            ttk.Entry(settings_lf, textvariable=self.ps_confirm_password, show="*").grid(row=2, column=1, sticky="ew",
                                                                                         padx=5, pady=5)

            save_button = ttk.Button(settings_lf, text="保存修改", command=self._user_save_own_password)
            save_button.grid(row=3, column=0, columnspan=2, pady=(15, 5), ipady=4)
    def _populate_users(self):
        """刷新用户列表"""
        self.user_tree.delete(*self.user_tree.get_children())
        sorted_users = sorted(self.all_data.get('user_accounts', {}).items(),
                              key=lambda item: (item[0] != 'admin', item[0]))
        for username, data in sorted_users:
            self.user_tree.insert("", "end", values=(username,))
        self._clear_user_fields()

    def _load_user_for_edit(self, event=None):
        """(管理员视图专用) 加载用户信息，并明文显示密码。"""
        selected_item = self.user_tree.focus()
        if not selected_item: return

        username = self.user_tree.item(selected_item, "values")[0]
        user_data = self.all_data['user_accounts'].get(username, {})

        self.um_username.set(username)

        # 管理员视图下，密码框明文显示
        self.um_password_entry.config(show="")
        self.um_password.set(user_data.get('password', ''))

        permissions = user_data.get('permissions', {})
        is_admin = (username == 'admin')

        for key, (var, cb) in self.um_permissions_vars.items():
            var.set(permissions.get(key, False))
            is_base_permission = (key == 'allow_tab_prescription')

            if is_admin or is_base_permission:
                cb.config(state='disabled')
            else:
                cb.config(state='normal')

        self.um_username_entry.config(state='disabled' if is_admin else 'normal')

    def _save_user(self):
        """(管理员视图专用) 保存用户信息。"""
        if self.um_username_entry.cget('state') == 'disabled':
            username = 'admin'
        else:
            username = self.um_username.get().lower().strip()

        if not username:
            messagebox.showerror("输入错误", "用户名不能为空！");
            return

        password_to_save = self.um_password.get().strip()
        if not password_to_save:
            messagebox.showerror("输入错误", "密码不能为空！");
            return

        if ' ' in username:
            messagebox.showerror("输入错误", "用户名不能包含空格！");
            return

        is_new_user = username not in self.all_data['user_accounts']
        if username == 'admin' and is_new_user:
            messagebox.showerror("权限错误", "不能创建名为 'admin' 的新用户。");
            return

        new_user_data = {'password': password_to_save}

        if username != 'admin':
            permissions = {'allow_tab_prescription': True}
            for key, (var, cb) in self.um_permissions_vars.items():
                permissions[key] = var.get()
            new_user_data['permissions'] = permissions
        else:
            new_user_data['permissions'] = self.all_data['user_accounts']['admin'].get('permissions', {})

        if is_new_user and username not in self.all_data['user_data']:
            self.all_data['user_data'][username] = {"prescriptions": [], "appointments": [], "sales_revenue": []}

        self.all_data['user_accounts'][username] = new_user_data
        self._save_database()
        self._populate_users()
        messagebox.showinfo("成功", f"用户 '{username}' 的信息已成功保存！")

    def _admin_login_as_user(self):
        """(V3 - 最终修复版) 使用正确的构造函数参数，根治管理员代管空白窗口的bug。"""
        selected_item = self.user_tree.focus()
        if not selected_item:
            messagebox.showwarning("操作无效", "请先从左侧列表选择一个要管理的用户。")
            return

        target_username = self.user_tree.item(selected_item, "values")[0]

        if target_username == 'admin':
            messagebox.showinfo("提示", "您已登录为管理员，无需再次登录。")
            return

        target_user_info = self.all_data['user_accounts'].get(target_username)
        if not target_user_info:
            messagebox.showerror("数据错误", f"在数据库中找不到用户 '{target_username}' 的账户信息。")
            return

        target_permissions = target_user_info.get('permissions', {})

        admin_view_window = tk.Toplevel(self.root)
        admin_view_window.geometry("1100x700")
        admin_view_window.minsize(950, 600)

        # ▼▼▼▼▼ 核心修正：使用与 __main__ 中完全一致的、最新的调用格式 ▼▼▼▼▼
        MedicineApp(
            root=admin_view_window,
            file_path=self.csv_path,
            all_db_data=self.all_data,
            username=target_username,  # 明确传递 username
            permissions=target_permissions,  # 明确传递 permissions
            is_admin_view=True  # 明确告知这是代管模式
        )
        # ▲▲▲▲▲ 修正结束 ▲▲▲▲▲

        admin_view_window.grab_set()

    def _delete_user(self):
        username = self.um_username.get().lower().strip()
        if not username:
            messagebox.showwarning("操作无效", "请先从左侧列表选择要删除的用户。")
            return
        if username == 'admin':
            messagebox.showerror("权限错误", "不能删除管理员账号！")
            return

        if username in self.all_data['user_accounts']:
            if messagebox.askyesno("确认删除", f"确定要永久删除用户 '{username}' 吗？此操作无法撤销。"):

                # 1. 删除账号密码和权限
                del self.all_data['user_accounts'][username]

                # 2. ▼▼▼ 清理该用户遗留的所有业务数据（防止产生幽灵数据） ▼▼▼
                if username in self.all_data.get('user_data', {}):
                    del self.all_data['user_data'][username]
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                self._save_database()
                self._populate_users()
                messagebox.showinfo("成功", f"用户 '{username}' 及其关联数据已被彻底删除。")
        else:
            messagebox.showerror("错误", f"未找到名为 '{username}' 的用户。可能是表单未清空导致的。")
    def _clear_user_fields(self):
        """
        (V2 - 修复版)
        清空表单，准备创建新用户。
        核心修复：强制解锁用户名输入框，解决'永远是admin'无法输入的问题。
        """
        # 取消列表选中状态
        if hasattr(self, 'user_tree') and self.user_tree.selection():
            self.user_tree.selection_remove(self.user_tree.selection())

        # 清空变量
        self.um_username.set("")
        self.um_password.set("")
        self.um_password_entry.config(show="") # 明文显示密码

        # 重置所有权限勾选框
        for var, cb in self.um_permissions_vars.values():
            var.set(False)
            cb.config(state='normal')

        # 默认给予基础权限 (药方查看)
        if 'allow_tab_prescription' in self.um_permissions_vars:
            var, cb = self.um_permissions_vars['allow_tab_prescription']
            var.set(True)
            # cb.config(state='disabled') # 可选：是否强制给基础权限

        # ▼▼▼ 核心修复：解锁输入框 ▼▼▼
        self.um_username_entry.config(state='normal')
        self.um_username_entry.focus_set()
    def _apply_permission_template(self, template_name):
        """根据模板名称，一键勾选/取消勾选权限。"""
        if self.um_username_entry.cget('state') == 'disabled' or self.um_username.get() == 'admin':
            messagebox.showwarning("操作无效", "不能对管理员账户应用权限模板。")
            return

        templates = {
            'reception': {
                'allow_tab_appointment': True, 'allow_btn_appt_save': True,
                'allow_btn_appt_find': True, 'allow_btn_appt_delete': True,
                'allow_btn_appt_clear_fields': True, 'allow_btn_appt_export_excel': True,
                'export_appt_include_amount': True, 'allow_btn_presc_save': True, 'allow_btn_presc_history': True,
                'allow_btn_presc_find': True, 'allow_btn_presc_calculator': True,
                'allow_btn_presc_clear': True, 'allow_btn_presc_export': True,
            },
            'pharmacist': {
                'allow_btn_presc_save': True, 'allow_btn_presc_history': True,
                'allow_btn_presc_find': True, 'allow_btn_presc_calculator': True,
                'allow_btn_presc_clear': True, 'allow_btn_presc_export': True,
            },
            'doctor': {
                'allow_tab_appointment': True,
                'allow_btn_appt_save': True, 'allow_btn_appt_export_excel': True,
                'export_appt_include_amount': True,
            }
        }
        target_perms = templates.get(template_name, {})
        for key, (var, cb) in self.um_permissions_vars.items():
            if key != 'allow_tab_prescription':
                var.set(target_perms.get(key, False))

    def _user_save_own_password(self):
        """(普通用户专用) 处理用户修改自己密码的逻辑。"""
        current_pass = self.ps_current_password.get()
        new_pass = self.ps_new_password.get()
        confirm_pass = self.ps_confirm_password.get()

        if not new_pass and not confirm_pass:
            messagebox.showinfo("提示", "您没有输入新密码，密码未被修改。", parent=self.root)
            return

        if not current_pass:
            messagebox.showerror("输入错误", "必须输入当前密码才能进行修改！", parent=self.root)
            return

        user_data = self.all_data['user_accounts'].get(self.username)
        if not user_data or user_data.get('password') != current_pass:
            messagebox.showerror("验证失败", "当前密码不正确！", parent=self.root)
            return

        if new_pass != confirm_pass:
            messagebox.showerror("输入错误", "两次输入的新密码不一致！", parent=self.root)
            return

        if len(new_pass) < 3:
            messagebox.showwarning("提示", "为了安全，建议密码长度至少为3位。", parent=self.root)

        self.all_data['user_accounts'][self.username]['password'] = new_pass
        self._save_database()

        self.ps_current_password.set("")
        self.ps_new_password.set("")
        self.ps_confirm_password.set("")
        messagebox.showinfo("成功", "您的密码已成功修改！", parent=self.root)

    # 文件: your_script.py
    # 函数: _sync_all_external_configs

    def _sync_all_external_configs(self, medicine_csv_path):
        """
        [V8 - 实时调试报告版]
        1. 强制读取 commissionRate.csv。
        2. 启动时弹出窗口，汇报读取到的所有列名和老师名字。
        3. 帮助定位为什么新老师没读出来。
        """
        needs_saving = False
        import pandas as pd
        import os
        from tkinter import messagebox

        # 定义读取函数
        def robust_read_csv(filepath, header='infer'):
            try:
                return pd.read_csv(filepath, encoding='utf-8', header=header)
            except UnicodeDecodeError:
                return pd.read_csv(filepath, encoding='gbk', header=header)

        # ====================
        # 1. 药品数据 (这部分应该没问题，保持原样)
        # ====================
        if os.path.exists(medicine_csv_path):
            try:
                df_medicine = robust_read_csv(medicine_csv_path, header=None)
                if df_medicine.shape[1] >= 6:
                    new_medicine_data = {}
                    names = df_medicine.iloc[:, 2]
                    infos = df_medicine.iloc[:, 3]
                    prices_col = pd.to_numeric(df_medicine.iloc[:, 5], errors='coerce')
                    for i in range(len(names)):
                        name_part = str(names.iloc[i]).strip()
                        info_part = str(infos.iloc[i]).strip()
                        full_name = f"{name_part} ({info_part})" if pd.notna(
                            infos.iloc[i]) and info_part and info_part.lower() != 'nan' else name_part
                        if pd.notna(name_part) and name_part and pd.notna(prices_col.iloc[i]):
                            new_medicine_data[full_name] = {'price': float(prices_col.iloc[i]),
                                                            'unit': str(df_medicine.iloc[i, 4]).strip() or '克'}

                    if new_medicine_data != self.all_data['config_data'].get('medicine_data', {}):
                        self.all_data['config_data']['medicine_data'] = new_medicine_data
                        needs_saving = True
            except Exception:
                pass

        # ====================
        # 2. 提成与老师 (调试核心)
        # ====================
        debug_log = []  # 用于收集调试信息

        if os.path.exists('commissionRate.csv'):
            try:
                # 读取CSV
                df_commission = robust_read_csv('commissionRate.csv', header=0)
                df_commission.columns = df_commission.columns.str.strip()  # 去空格

                # 记录表头信息
                debug_log.append(f"【表头列名】: {list(df_commission.columns)}")

                if not df_commission.empty:
                    # ▼▼▼ 锁定老师列 ▼▼▼
                    # 根据您的截图：第1列是部门，第2列(索引1)是老师
                    teacher_col = None

                    # 优先找名字匹配
                    for col in df_commission.columns:
                        if "老师" in str(col) or "姓名" in str(col):
                            teacher_col = col
                            break

                    # 兜底：如果找不到名字，强制用第2列
                    if teacher_col is None and len(df_commission.columns) >= 2:
                        teacher_col = df_commission.columns[1]
                        debug_log.append(f"未找到'老师'列名，强制使用第2列: {teacher_col}")
                    elif teacher_col:
                        debug_log.append(f"已锁定老师列: {teacher_col}")
                    else:
                        debug_log.append("错误：无法确定老师列，CSV列数不足2列！")
                        messagebox.showerror("调试报错", "\n".join(debug_log))
                        return []

                    # 寻找数据列
                    dispensing_col = next((c for c in df_commission.columns if '出药' in c), None)
                    tcm_col = next((c for c in df_commission.columns if '中医' in c), None)
                    physio_col = next((c for c in df_commission.columns if '理疗' in c), None)
                    card_col = next((c for c in df_commission.columns if '办卡' in c), None)

                    final_teachers = []
                    final_specialties = {}
                    commission_rows = []

                    # 用于弹窗显示的“已读取名单”
                    names_found = []

                    # 遍历每一行
                    for idx, row in df_commission.iterrows():
                        raw_name = row[teacher_col]
                        name = str(raw_name).strip()

                        # 过滤无效行
                        if not name or name.lower() == 'nan':
                            continue

                        names_found.append(name)  # 记录读到的名字

                        # --- 沈志强/出药分裂逻辑 ---
                        has_dispensing = False
                        if dispensing_col and pd.notna(row[dispensing_col]):
                            try:
                                has_dispensing = float(row[dispensing_col]) > 0
                            except:
                                pass

                        if has_dispensing:
                            name_dispensing = f"{name}（出药）"
                            name_physio = f"{name}（不出药）"
                            final_teachers.extend([name_dispensing, name_physio])

                            if "沈志强" in name:
                                final_specialties[name_dispensing] = ['中医']
                                final_specialties[name_physio] = ['中医']
                                row_disp = {teacher_col: name_dispensing}
                                if tcm_col: row_disp[tcm_col] = row[dispensing_col]
                                commission_rows.append(row_disp)
                                row_phys = {teacher_col: name_physio}
                                if tcm_col: row_phys[tcm_col] = row.get(tcm_col, 0)
                                commission_rows.append(row_phys)
                            else:
                                final_specialties[name_dispensing] = ['出药']
                                final_specialties[name_physio] = ['理疗']
                                commission_rows.append(
                                    {teacher_col: name_dispensing, dispensing_col: row[dispensing_col]})
                                if physio_col: commission_rows.append(
                                    {teacher_col: name_physio, physio_col: row[physio_col]})
                        else:
                            # --- 普通/新老师逻辑 ---
                            final_teachers.append(name)

                            has_tcm = False
                            if tcm_col and pd.notna(row[tcm_col]):
                                try:
                                    has_tcm = float(row[tcm_col]) > 0
                                except:
                                    pass

                            has_physio = False
                            if physio_col and pd.notna(row[physio_col]):
                                try:
                                    has_physio = float(row[physio_col]) > 0
                                except:
                                    pass

                            # 判定逻辑
                            allowed = []
                            if has_tcm and not has_physio:
                                allowed = ['中医']
                            elif not has_tcm and has_physio:
                                allowed = ['理疗']
                            else:
                                allowed = ['中医', '理疗']

                            final_specialties[name] = allowed
                            commission_rows.append(row.to_dict())

                    # 重建数据表
                    new_df = pd.DataFrame(commission_rows)
                    if not new_df.empty:
                        final_rules = new_df.set_index(teacher_col)
                    else:
                        final_rules = pd.DataFrame()

                    for col in ["中医", "理疗", "出药", "办卡充值"]:
                        if col not in final_rules.columns: final_rules[col] = 0.0

                    if card_col and card_col in final_rules.columns:
                        final_rules["办卡充值"] = final_rules[card_col].fillna(0.05)
                    else:
                        final_rules["办卡充值"] = 0.05

                    if "未指定" not in final_teachers: final_teachers.append("未指定")

                    # 排序
                    final_teachers = sorted(list(set(final_teachers)))

                    # 更新配置
                    self.all_data['config_data']['commission_rules'] = final_rules
                    self.all_data['config_data']['teacher_specialties'] = final_specialties
                    self.all_data['config_data']['teachers'] = final_teachers

                    needs_saving = True

                    # ▼▼▼ 弹窗汇报结果 ▼▼▼
                    # 这样您就知道到底是没读到文件，还是读错了列，还是名字被过滤了
                    report_msg = (
                        f"CSV 文件路径: {os.path.abspath('commissionRate.csv')}\n"
                        f"锁定列名: {teacher_col}\n"
                        f"--------------------------------\n"
                        f"成功读取到 {len(names_found)} 个原始名字:\n"
                        f"{', '.join(names_found)}\n"
                        f"--------------------------------\n"
                        f"如果不包含您的新人，请检查CSV是否已保存！"
                    )
                    messagebox.showinfo("配置同步调试报告", report_msg)

            except Exception as e:
                import traceback
                err_msg = traceback.format_exc()
                messagebox.showerror("配置更新严重错误", f"读取 commissionRate.csv 失败：\n{e}\n\n{err_msg}")

        else:
            messagebox.showwarning("警告", "未找到 commissionRate.csv 文件！无法更新老师列表。")

        # 3. 付款方式 (不变)
        if os.path.exists('payment_methods.csv'):
            try:
                df = robust_read_csv('payment_methods.csv', header=None)
                new_list = sorted(list(set(df[0].dropna().astype(str).str.strip().tolist())))
                if new_list != self.all_data['config_data'].get('payment_methods', []):
                    self.all_data['config_data']['payment_methods'] = new_list
                    needs_saving = True
            except Exception:
                pass

        if needs_saving:
            self._save_database()

        return []
    def _on_doses_changed(self, event=None):
        self.update_prescription_display()

    # 注意，我们给函数增加了一个参数 doses_text=None
    def update_prescription_display(self):  # 注意：括号里不再有 doses_text
        self.tree.delete(*self.tree.get_children())
        total_grams = 0.0
        total_price = 0.0

        # 这部分不变，计算单剂药的总价
        for i, item in enumerate(self.prescription):
            tag = 'oddrow' if i % 2 == 1 else 'evenrow'
            gram_str = f"{item['grams']:.3f}".rstrip('0').rstrip('.')
            self.tree.insert("", "end", values=(item['name'], gram_str, f"{item['subtotal']:.2f}"), tags=(tag,))
            total_grams += item['grams']
            total_price += item['subtotal']

        self.total_grams_label.config(text=f"{total_grams:.2f} 克")
        self.total_price_label.config(text=f"{total_price:.2f} 元")

        # --- 核心修改在这里 ---
        # 1. 不再接收参数，而是每次都主动去输入框获取最新文本
        doses_text = self.doses_entry.get()

        # 2. 用获取到的最新文本进行计算
        try:
            doses = int(doses_text) if doses_text else 1
            if doses < 1:
                doses = 1
        except (ValueError, TypeError):
            # 如果输入了无效字符（比如'abc'），也按1剂算
            doses = 1

        final_total = total_price * doses
        self.final_total_label.config(text=f"{final_total:.2f} 元")

    def _load_data_sources(self):
        import pandas as pd
        try:
            try:
                df_teachers = pd.read_csv('teachers.csv', header=None, encoding='utf-8')
            except UnicodeDecodeError:
                df_teachers = pd.read_csv('teachers.csv', header=None, encoding='gbk')
            self.teacher_list = df_teachers[0].dropna().tolist()
        except FileNotFoundError:
            self.teacher_list = ["默认老师"];
            messagebox.showwarning("文件未找到", "未找到 teachers.csv。")
        except Exception as e:
            self.teacher_list = ["默认老师"];
            messagebox.showwarning("文件读取错误", f"读取 teachers.csv 时出错: {e}")

        # --- 关键修改：确保“未指定”老师存在 ---
        if "未指定" not in self.teacher_list:
            self.teacher_list.append("未指定")

        self._generate_teacher_pinyin_map()
        try:
            try:
                df_payment = pd.read_csv('payment_methods.csv', header=None, encoding='utf-8')
            except UnicodeDecodeError:
                df_payment = pd.read_csv('payment_methods.csv', header=None, encoding='gbk')
            self.payment_methods = df_payment[0].dropna().tolist()
        except FileNotFoundError:
            self.payment_methods = ["微信", "支付宝"];
            messagebox.showwarning("文件未找到",
                                   "未找到 payment_methods.csv。")
        except Exception as e:
            self.payment_methods = ["微信", "支付宝"];
            messagebox.showwarning("文件读取错误",
                                   f"读取 payment_methods.csv 时出错: {e}")

    # 文件: your_script.py
    # 函数: _generate_pinyin_maps (注意末尾的's')

    # ▼▼▼▼▼ 用下面的代码完整替换整个函数 ▼▼▼▼▼
    def _generate_pinyin_maps(self):
        """
        [最终正确版] 生成所有用于搜索的拼音映射。
        """
        # --- 1. 生成药品拼音映射 (这部分逻辑不变) ---
        self.medicine_pinyin_map.clear()
        medicine_data = self.all_data['config_data'].get('medicine_data', {})
        for name in medicine_data.keys():
            base_name = name.split(' (')[0]
            pinyin_list = lazy_pinyin(base_name)
            full = "".join(pinyin_list)
            self.medicine_pinyin_map[name] = {
                'initials': "".join(p[0] for p in pinyin_list),
                'syllable_initials': [p[0] for p in pinyin_list],
                'full': full,
                'fuzzy_full': self._get_fuzzy_string(full)
            }

        # --- 2. 生成老师拼音映射 (使用最新的正确逻辑) ---
        self.teacher_pinyin_map.clear()
        teacher_list = self.all_data['config_data'].get('teachers', ["默认老师"])

        for name in teacher_list:
            full_name_stripped = name.strip()
            if not full_name_stripped:
                continue

            # 核心修改：在生成拼音前，先用正则表达式移除括号和括号里的内容
            base_name = re.sub(r'[\(（].*?[\)）]', '', full_name_stripped).strip()

            if not base_name:
                base_name = full_name_stripped  # 使用原始名字作为备用

            pinyin_list = lazy_pinyin(base_name)
            full_pinyin = "".join(pinyin_list)
            initials = "".join(p[0] for p in pinyin_list)

            # 存储所有需要的数据，确保 'base_name' 键存在
            self.teacher_pinyin_map[name] = {
                'base_name': base_name,
                'initials': initials,
                'full': full_pinyin,
            }

    def _search_teacher(self, event):
        if event.keysym in ("Up", "Down", "Return", "Enter", "Tab"): return
        search_term = self.teacher_entry.get().lower().strip()
        if not search_term:
            if self.teacher_results_listbox.winfo_viewable(): self.teacher_results_listbox.grid_remove()
            return
        matches = []
        for full_name, pinyin_data in self.teacher_pinyin_map.items():
            base_name = pinyin_data['base_name'].lower()
            initials = pinyin_data['initials']
            full_pinyin = pinyin_data['full']
            priority = 0
            if base_name.startswith(search_term):
                priority = 1
            elif initials.startswith(search_term):
                priority = 2
            elif full_pinyin.startswith(search_term):
                priority = 3
            elif search_term in base_name:
                priority = 4
            elif search_term in initials:
                priority = 5
            elif search_term in full_pinyin:
                priority = 6
            if priority > 0: matches.append((priority, full_name))
        self.teacher_results_listbox.delete(0, tk.END)
        if matches:
            matches.sort()
            seen = set()
            for _, name in matches:
                if name not in seen:
                    self.teacher_results_listbox.insert(tk.END, name)
                    seen.add(name)
            self._show_teacher_listbox()
        else:
            if self.teacher_results_listbox.winfo_viewable(): self.teacher_results_listbox.grid_remove()
    def _show_teacher_listbox(self):
        """显示老师搜索结果列表框"""
        if not self.teacher_results_listbox.winfo_viewable():
            self.teacher_results_listbox.grid(row=1, column=0, sticky="ew")
            self.teacher_results_listbox.lift()

    def _hide_teacher_listbox(self, event=None):
        """在短暂延迟后隐藏老师搜索结果列表框"""
        self.root.after(150, self._perform_hide)

    def _perform_hide(self):
        """实际执行隐藏列表框的动作"""
        try:
            focused_widget = self.root.focus_get()
            if focused_widget not in (self.teacher_entry, self.teacher_results_listbox):
                if self.teacher_results_listbox.winfo_viewable():
                    self.teacher_results_listbox.grid_remove()
        except (KeyError, tk.TclError):
            if self.teacher_results_listbox.winfo_viewable():
                self.teacher_results_listbox.grid_remove()

    def _navigate_teacher_listbox(self, event):
        """用键盘导航老师搜索结果列表框"""
        if not self.teacher_results_listbox.winfo_viewable():
            # 如果列表不可见，按向下键应该让它可见
            if self.teacher_results_listbox.size() > 0:
                self._show_teacher_listbox()
            return "break"

        lb = self.teacher_results_listbox
        sel = lb.curselection()
        current = sel[0] if sel else -1
        if event.keysym == "Down":
            next_idx = min(current + 1, lb.size() - 1)
        else:
            next_idx = max(current - 1, 0)
        if next_idx >= 0:
            lb.selection_clear(0, tk.END)
            lb.selection_set(next_idx)
            lb.activate(next_idx)
            lb.see(next_idx)
        return "break"

    def _confirm_teacher_selection(self, event=None):
        """(V3 - 加入膏药)"""
        if not self.teacher_results_listbox.winfo_viewable(): return
        lb = self.teacher_results_listbox
        sel = lb.curselection()

        if not sel and lb.size() > 0:
            lb.selection_set(0)
            sel = lb.curselection()

        if sel:
            teacher_name = lb.get(sel[0])
            self.teacher_entry.delete(0, tk.END)
            self.teacher_entry.insert(0, teacher_name)
            lb.grid_remove()

            teacher_specialties = self.all_data['config_data'].get('teacher_specialties', {})
            base_specialties = teacher_specialties.get(teacher_name, [])

            if not base_specialties:
                if "理疗" in teacher_name:
                    base_specialties = ["理疗"]
                else:
                    base_specialties = ["中医", "理疗"]

            new_values = []
            for s in base_specialties:
                if s != "出药": new_values.append(s)

            # ▼▼▼ 核心修改：加入 膏药 ▼▼▼
            common_items = ["办卡充值", "茶包", "足浴包", "膏药"]
            for item in common_items:
                if item not in new_values:
                    new_values.append(item)

            self.type_combobox['values'] = new_values
            self.type_combobox.config(state='readonly')

            current_type = self.type_combobox.get()
            if current_type not in new_values:
                self.type_combobox.set('')

            self.type_combobox.focus_set()

        return "break"
    def create_widgets(self):
        try:
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            style = ttk.Style()
            default_font = ("Microsoft YaHei", 10)
            style.configure(".", font=default_font)
            style.configure("Treeview", rowheight=28, font=default_font)
            style.configure("Treeview.Heading", font=(default_font[0], default_font[1], "bold"))

            self.notebook = ttk.Notebook(self.root)
            self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

            # 1. 药方管理
            if self.permissions.get('allow_tab_prescription'):
                try:
                    self.prescription_frame = ttk.Frame(self.notebook)
                    self.prescription_frame.columnconfigure(1, weight=1)
                    self.prescription_frame.rowconfigure(0, weight=1)
                    self.notebook.add(self.prescription_frame, text="药方管理")
                    self._create_prescription_widgets()
                    self._bind_prescription_events()
                    self.populate_full_list()
                except Exception: pass

            # 2. 信息登记
            if self.permissions.get('allow_tab_appointment'):
                try:
                    self.appointment_frame = ttk.Frame(self.notebook)
                    self.notebook.add(self.appointment_frame, text="信息登记")
                    self._create_appointment_widgets()
                except Exception: pass

            # 3. 支出统计
            if self.permissions.get('allow_tab_expense'):
                try:
                    self.expense_frame = ttk.Frame(self.notebook)
                    self.notebook.add(self.expense_frame, text="支出统计")
                    self._create_expense_widgets()
                except Exception: pass

            # 4. 提成统计
            if self.permissions.get('allow_tab_commission'):
                try:
                    self.commission_frame = ttk.Frame(self.notebook)
                    self.commission_frame.columnconfigure(0, weight=1)
                    self.commission_frame.rowconfigure(1, weight=1)
                    self.notebook.add(self.commission_frame, text="提成统计")
                    self._create_commission_widgets()
                except Exception: pass

            # 5. 用户管理
            if self.permissions.get('allow_tab_usermanagement'):
                try:
                    self.user_management_frame = ttk.Frame(self.notebook)
                    self.user_management_frame.columnconfigure(0, weight=1)
                    self.user_management_frame.rowconfigure(0, weight=1)
                    self.notebook.add(self.user_management_frame, text="用户管理")
                    self._create_user_and_role_management_widgets()
                except Exception: pass

            # --- [已删除] 使用帮助页面 ---

            self._bind_common_events()
            self._apply_role_permissions()
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        except Exception as e:
            messagebox.showerror("错误", f"界面创建失败: {e}")
            self.root.destroy()
    def _apply_role_permissions(self):
        """
        (V8 - 全面覆盖版)
        安全地应用权限，包含新的 [支出统计] 按钮控制。
        """
        # 1. 药方
        if self.permissions.get('allow_tab_prescription'):
            p_map = {
                'allow_btn_presc_save': 'save_prescription_button',
                'allow_btn_presc_history': 'history_button',
                'allow_btn_presc_find': 'find_button',
                'allow_btn_presc_calculator': 'calculator_button',
                'allow_btn_presc_clear': 'clear_button',
                'allow_btn_presc_export': 'export_button',
            }
            for perm, attr in p_map.items():
                if not self.permissions.get(perm, False):
                    try: getattr(self, attr).grid_remove()
                    except: pass

        # 2. 营业登记
        if self.permissions.get('allow_tab_appointment'):
            a_map = {
                'allow_btn_appt_save': 'save_appointment_button',
                'allow_btn_appt_find': 'find_appointment_button',
                'allow_btn_appt_delete': 'delete_appointment_button',
                'allow_btn_appt_export_excel': 'export_appointments_button',
                'allow_btn_appt_export_lemon': 'export_lemon_button',
                'allow_btn_appt_clear_fields': 'clear_fields_button'
            }
            for perm, attr in a_map.items():
                if not self.permissions.get(perm, False):
                    try: getattr(self, attr).pack_forget()
                    except: pass

        # 3. 支出统计 (▼▼▼ 新增 ▼▼▼)
        if self.permissions.get('allow_tab_expense'):
            e_map = {
                'allow_btn_exp_save': 'exp_save_button',
                'allow_btn_exp_delete': 'exp_delete_button',
                # 两个导出按钮共享一个权限
                'allow_btn_exp_export': ['exp_export_excel_button', 'exp_export_lemon_button']
            }
            for perm, attrs in e_map.items():
                if not self.permissions.get(perm, False):
                    # 兼容单个属性名或属性名列表
                    if isinstance(attrs, str): attrs = [attrs]
                    for attr in attrs:
                        try: getattr(self, attr).pack_forget()
                        except: pass
    def _save_global_settings(self):
        """(可选同步版) 只负责保存“共享视图模式”的开关状态。"""
        if 'config_data' not in self.all_data:
            self.all_data['config_data'] = {}

        self.all_data['config_data']['enable_global_data_sharing'] = self.global_share_var.get()
        self._save_database()
        messagebox.showinfo(
            "设置已保存",
            "共享视图模式设置已更新。\n\n此设置将在下次重启程序或切换账号后对所有用户生效。",
            parent=self.root
        )

    def _sync_all_data_to_admin(self):
        """(管理员专用) 手动将所有用户的新数据增量同步到admin账户。"""
        if not messagebox.askyesno("确认操 作",
                                   "您确定要将所有用户的数据同步到admin账户吗？\n\n"
                                   "此操作只会添加admin账户中不存在的新记录，不会覆盖任何现有数据。\n\n"
                                   "建议在所有用户都已下线时执行此操作。",
                                   parent=self.root):
            return

        admin_prescriptions = self.all_data['user_data']['admin']['prescriptions']
        admin_appointments = self.all_data['user_data']['admin']['appointments']
        admin_sales = self.all_data['user_data']['admin']['sales_revenue']  # 新增

        # 为了高效查找，先将admin现有数据的ID存入集合
        existing_presc_ids = {p['id'] for p in admin_prescriptions}
        existing_appt_ids = {a['id'] for a in admin_appointments}
        existing_sales_ids = {s['id'] for s in admin_sales}  # 新增

        total_synced_presc = 0
        total_synced_appt = 0
        total_synced_sales = 0  # 新增

        for user, user_data_content in self.all_data.get('user_data', {}).items():
            if user == 'admin':
                continue

            # 同步药方
            for presc in user_data_content.get('prescriptions', []):
                if presc['id'] not in existing_presc_ids:
                    admin_prescriptions.append(presc)
                    existing_presc_ids.add(presc['id'])  # 实时更新集合
                    total_synced_presc += 1

            # 同步预约
            for appt in user_data_content.get('appointments', []):
                if appt['id'] not in existing_appt_ids:
                    admin_appointments.append(appt)
                    existing_appt_ids.add(appt['id'])
                    total_synced_appt += 1

            # ▼▼▼▼▼ 新增：同步销售收入 ▼▼▼▼▼
            for sale in user_data_content.get('sales_revenue', []):
                if sale['id'] not in existing_sales_ids:
                    admin_sales.append(sale)
                    existing_sales_ids.add(sale['id'])
                    total_synced_sales += 1
            # ▲▲▲▲▲ 新增结束 ▲▲▲▲▲

        if total_synced_presc > 0 or total_synced_appt > 0 or total_synced_sales > 0:  # 条件更新
            self._save_database()
            messagebox.showinfo("同步完成",
                                f"数据同步成功！\n\n"
                                f"新增药方记录: {total_synced_presc} 条\n"
                                f"新增预约记录: {total_synced_appt} 条\n"
                                f"新增销售记录: {total_synced_sales} 条\n\n"  # 新增
                                "数据已保存。",
                                parent=self.root
                                )
        else:
            messagebox.showinfo("同步完成", "没有发现任何新的数据需要同步。", parent=self.root)

    def _migrate_data_to_admin(self):
        """
        (一次性操作) 将所有非admin账户的数据迁移到admin账户，并清空原数据。
        返回迁移的记录数统计。
        """
        admin_prescriptions = self.all_data['user_data']['admin']['prescriptions']
        admin_appointments = self.all_data['user_data']['admin']['appointments']

        total_migrated_presc = 0
        total_migrated_appt = 0

        for user, user_data_content in self.all_data.get('user_data', {}).items():
            if user == 'admin':
                continue  # 跳过管理员自己

            # 迁移药方
            prescs_to_move = user_data_content.get('prescriptions', [])
            if prescs_to_move:
                admin_prescriptions.extend(prescs_to_move)
                total_migrated_presc += len(prescs_to_move)
                prescs_to_move.clear()  # 清空原列表
                print(f"已将用户 [{user}] 的 {len(prescs_to_move)} 条药方迁移至 admin。")

            # 迁移预约
            appts_to_move = user_data_content.get('appointments', [])
            if appts_to_move:
                admin_appointments.extend(appts_to_move)
                total_migrated_appt += len(appts_to_move)
                appts_to_move.clear()  # 清空原列表
                print(f"已将用户 [{user}] 的 {len(appts_to_move)} 条预约迁移至 admin。")

        return {"prescriptions": total_migrated_presc, "appointments": total_migrated_appt}

    def _on_tab_changed(self, event):
        """当标签页切换时触发"""
        try:
            selected_tab_text = self.notebook.tab(self.notebook.select(), "text")

            if selected_tab_text == "信息登记":
                self._populate_appointment_treeview()
            elif selected_tab_text == "提成统计":
                self._populate_commission_treeview()
            # ▼▼▼▼▼ 新增：切换到销售收入页面时刷新列表 ▼▼▼▼▼
            elif selected_tab_text == "销售收入":
                self._populate_sales_treeview()
            # ▲▲▲▲▲ 新增结束 ▲▲▲▲▲
        except tk.TclError:
            pass

    def _create_prescription_widgets(self):
        control_frame = ttk.Frame(self.prescription_frame, padding="10")
        control_frame.grid(row=0, column=0, sticky="nsew")
        prescription_panel = ttk.Frame(self.prescription_frame, padding="10")
        prescription_panel.grid(row=0, column=1, sticky="nsew")
        self.prescription_frame.columnconfigure(1, weight=1);
        self.prescription_frame.rowconfigure(0, weight=1);
        control_frame.rowconfigure(2, weight=1)
        ttk.Label(control_frame, text="输入药名或拼音 (支持模糊搜索):").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(control_frame, font=("Microsoft YaHei", 11))
        self.name_entry.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.search_results_listbox = tk.Listbox(control_frame, font=("Microsoft YaHei", 10))
        self.search_results_listbox.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5)
        ttk.Label(control_frame, text="输入剂量:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        dose_frame = ttk.Frame(control_frame)
        dose_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.grams_entry = ttk.Entry(dose_frame, font=("Microsoft YaHei", 11))
        self.grams_entry.pack(side="left", fill="x", expand=True)
        self.unit_combobox = ttk.Combobox(dose_frame, values=self.unit_options, width=12, font=("Microsoft YaHei", 10))
        self.unit_combobox.set('克')
        self.unit_combobox.pack(side="left", padx=(5, 0))
        action_frame = ttk.Frame(control_frame);
        action_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0));
        action_frame.columnconfigure((0, 1), weight=1)
        self.add_button = ttk.Button(action_frame, text="添 加 / 更 新", command=self.add_or_update_prescription)
        self.add_button.grid(row=0, column=0, columnspan=2, sticky="ew", ipady=5, pady=(0, 5))
        self.save_prescription_button = ttk.Button(action_frame, text="保存药方",
                                                   command=self.save_current_prescription_to_db)
        self.save_prescription_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        self.history_button = ttk.Button(action_frame, text="历史记录", command=self.open_prescription_history_window)
        self.history_button.grid(row=2, column=0, sticky="ew")
        self.find_button = ttk.Button(action_frame, text="查找药方", command=self.open_find_dialog)
        self.find_button.grid(row=2, column=1, sticky="ew", padx=(5, 0))
        self.calculator_button = ttk.Button(action_frame, text="计算器", command=self.open_calculator)
        self.calculator_button.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        self.clear_button = ttk.Button(action_frame, text="全部清空", command=self.clear_all)
        self.clear_button.grid(row=3, column=1, sticky="ew", pady=(5, 0), padx=(5, 0))

        # ▼▼▼▼▼ 核心修改：按钮文字和命令 ▼▼▼▼▼
        self.export_button = ttk.Button(action_frame, text="导出至柠檬云",
                                        command=self.export_prescriptions_for_lemon_cloud)
        # ▲▲▲▲▲ 修改结束 ▲▲▲▲▲

        self.export_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        info_frame = ttk.LabelFrame(control_frame, text=" 药品信息 ", padding=8);
        info_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0));
        info_frame.columnconfigure(1, weight=1)
        ttk.Label(info_frame, text="单价:").grid(row=0, column=0, sticky="w")
        self.info_price_label = ttk.Label(info_frame, text="- -", font=("", 10, "bold"), foreground="navy")
        self.info_price_label.grid(row=0, column=1, sticky="w", padx=5)
        patient_info_frame = ttk.Frame(prescription_panel);
        patient_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(patient_info_frame, text="姓名:").grid(row=0, column=0, padx=(0, 5))
        ttk.Entry(patient_info_frame, textvariable=self.patient_name_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(patient_info_frame, text="日期:").grid(row=0, column=2, padx=(10, 5))
        ttk.Entry(patient_info_frame, textvariable=self.date_var).grid(row=0, column=3, sticky="ew")
        ttk.Label(patient_info_frame, text="剂数:").grid(row=0, column=4, padx=(10, 5))
        self.doses_entry = ttk.Entry(patient_info_frame, textvariable=self.doses_var, width=5)
        self.doses_entry.grid(row=0, column=5)
        self.doses_entry.bind("<KeyRelease>", self._on_doses_changed)
        patient_info_frame.columnconfigure((1, 3), weight=1)
        tree_frame = ttk.Frame(prescription_panel);
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=3)
        cols = ("name", "grams", "subtotal")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode="extended")
        self.tree.heading("name", text="药名");
        self.tree.heading("grams", text="克数/数量");
        self.tree.heading("subtotal", text="小计 (元)")
        self.tree.column("name", width=200, anchor='center');
        self.tree.column("grams", width=100, anchor='center');
        self.tree.column("subtotal", width=100, anchor='center')
        self.tree.tag_configure('oddrow', background='#F0F0F0');
        self.tree.tag_configure('evenrow', background='white')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview);
        self.tree.configure(yscrollcommand=vsb.set);
        self.tree.pack(side="left", fill="both", expand=True);
        vsb.pack(side="right", fill="y")
        summary_labelframe = ttk.LabelFrame(prescription_panel, text=" 费用总计 ", padding=8);
        summary_labelframe.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0));
        summary_labelframe.columnconfigure(1, weight=1)
        ttk.Label(summary_labelframe, text="总克数:", anchor="e").grid(row=0, column=0, sticky="ew")
        self.total_grams_label = ttk.Label(summary_labelframe, text="0.0 克", anchor="w");
        self.total_grams_label.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(summary_labelframe, text="单剂价格:", anchor="e").grid(row=1, column=0, sticky="ew")
        self.total_price_label = ttk.Label(summary_labelframe, text="0.00 元", anchor="w");
        self.total_price_label.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(summary_labelframe, text="应付总额:", font=("", 11, "bold"), anchor="e").grid(row=2, column=0,
                                                                                                sticky="ew",
                                                                                                pady=(5, 0))
        self.final_total_label = ttk.Label(summary_labelframe, text="0.00 元", font=("", 11, "bold"), foreground="blue",
                                           anchor="w");
        self.final_total_label.grid(row=2, column=1, sticky="ew", padx=5, pady=(5, 0))
        prescription_panel.rowconfigure(1, weight=1);
        prescription_panel.columnconfigure(0, weight=1)

    def export_prescriptions_for_lemon_cloud(self):
        import os, pythoncom, win32com.client as win32
        from datetime import datetime

        self._rebuild_view_lists()
        prescriptions_in_view = self.view_prescriptions
        if not prescriptions_in_view:
            messagebox.showinfo("提示", "没有已保存的历史药方记录可导出。")
            return

        # ▼▼▼▼▼ 核心修改 1：为每条记录预先计算好需要显示和导出的值 ▼▼▼▼▼
        display_data = []
        for record in prescriptions_in_view:
            total_price = sum(item.get('subtotal', 0) for item in record.get('prescription', []))
            try:
                doses = int(record.get('doses', 1))
            except:
                doses = 1
            final_total = total_price * doses

            # 创建一个包含所有需要信息的新字典
            display_record = record.copy()
            display_record['single_price'] = f"{total_price:.2f}"
            display_record['final_total'] = f"{final_total:.2f}"
            display_data.append(display_record)
        # ▲▲▲▲▲ 修改结束 ▲▲▲▲▲

        # 定义要在对话框中显示的字段
        display_fields = {
            'date': {'label': '日期'},
            'patient_name': {'label': '患者'},
            'single_price': {'label': '单价'},
            'final_total': {'label': '应付总额'}
        }

        dialog = AdvancedFilterDialog(self.root, "请勾选要导出的药方记录", display_data, display_fields)
        channel_frame = ttk.Frame(dialog.main_frame)
        # 将新控件放置在按钮框架之前
        channel_frame.pack(fill="x", pady=5, before=dialog.btn_frame)
        ttk.Label(channel_frame, text="导出渠道:").pack(side="left")
        channel_var = tk.StringVar(value="银行")
        ttk.Combobox(channel_frame, textvariable=channel_var, values=["银行", "现金"], state="readonly").pack(
            side="left", padx=5)
        dialog.extra_widgets['channel'] = channel_var

        selected_ids = dialog.show()

        if selected_ids is None: return

        # 从原始数据中筛选出最终要导出的记录
        target_prescriptions = [p for p in display_data if p.get('id') in selected_ids]
        if not target_prescriptions:
            messagebox.showinfo("提示", "没有选中任何有效的药方记录。")
            return

        # 弹出渠道选择框
        channel_window = tk.Toplevel(self.root)
        channel_window.title("选择渠道");
        channel_window.geometry("300x150")
        channel_window.transient(self.root);
        channel_window.grab_set()
        ttk.Label(channel_window, text="请为导出的药方选择渠道:").pack(pady=10)
        channel_var = tk.StringVar(value="银行")
        ttk.Combobox(channel_window, textvariable=channel_var, values=["银行", "现金"], state="readonly").pack(pady=5)
        result_channel = None

        def on_channel_confirm():
            nonlocal result_channel;
            result_channel = channel_var.get();
            channel_window.destroy()

        ttk.Button(channel_window, text="确认", command=on_channel_confirm).pack(pady=10)
        self.root.wait_window(channel_window)
        if result_channel is None: return

        template_filename = '银行日记账导入模板.xls' if result_channel == "银行" else '现金日记账导入模板.xls'

        def process_template_with_com(records, template_file):
            # (这个内部COM函数逻辑不变，因为它读取的是我们预处理好的'final_total')
            if not records: return 0, None
            template_path = os.path.join(os.getcwd(), template_file)
            if not os.path.exists(template_path): return -1, f"模板文件未找到：\n{template_path}"
            excel, workbook = None, None
            try:
                pythoncom.CoInitialize()
                excel = win32.Dispatch("Excel.Application")
                excel.Visible = False;
                excel.DisplayAlerts = False
                workbook = excel.Workbooks.Open(template_path)
                sheet = workbook.Sheets(1)
                header_map, col_c_letter, col_h_letter = {}, None, None
                for i in range(1, min(21, sheet.UsedRange.Rows.Count + 2)):
                    temp_map = {}
                    for j in range(1, sheet.UsedRange.Columns.Count + 1):
                        cell_val = sheet.Cells(i, j).Value
                        if cell_val:
                            cell_str = str(cell_val).strip()
                            temp_map[cell_str] = j
                            if cell_str == "收支类别名称":
                                col_c_letter = chr(ord('A') + j - 1)
                            elif cell_str == "项目":
                                col_h_letter = chr(ord('A') + j - 1)
                    if "日期" in temp_map and "摘要" in temp_map:
                        header_map = temp_map;
                        break
                if not header_map: raise ValueError("找不到标题行")

                xlUp = -4162
                last_row = sheet.Cells(sheet.Rows.Count, header_map["日期"]).End(xlUp).Row
                start_row = last_row + 1

                code_col_d_key = next((key for key in header_map if "收支类别编码" in key), None)
                code_col_d_index = header_map.get(code_col_d_key) if code_col_d_key else None
                code_col_i_key = next((key for key in header_map if "项目编码" in key), None)
                code_col_i_index = header_map.get(code_col_i_key) if code_col_i_key else None

                for i, record in enumerate(records):
                    current_row = start_row + i
                    try:
                        date_val = datetime.strptime(record.get('date', ''), '%Y-%m-%d')
                    except:
                        date_val = record.get('date', '')
                    summary_val = "收-销售收入"
                    project_val = "中药"
                    abstract_val = record.get('patient_name', '')
                    final_total = float(record.get('final_total', 0.0))  # 直接使用预计算的值

                    if "日期" in header_map: sheet.Cells(current_row, header_map["日期"]).Value = date_val
                    if "摘要" in header_map: sheet.Cells(current_row, header_map["摘要"]).Value = abstract_val
                    if "收支类别名称" in header_map: sheet.Cells(current_row,
                                                                 header_map["收支类别名称"]).Value = summary_val
                    if "收入（借方）" in header_map: sheet.Cells(current_row,
                                                               header_map["收入（借方）"]).Value = final_total
                    if "项目" in header_map: sheet.Cells(current_row, header_map["项目"]).Value = project_val
                    if "往来单位" in header_map: sheet.Cells(current_row, header_map["往来单位"]).Value = record.get(
                        'patient_name', '')

                    if code_col_d_index and col_c_letter:
                        formula_d = f'=IF(ISERROR(VLOOKUP({col_c_letter}{current_row},收支类别参考表!A:B,2,FALSE)),"",VLOOKUP({col_c_letter}{current_row},收支类别参考表!A:B,2,FALSE))'
                        sheet.Cells(current_row, code_col_d_index).Formula = formula_d
                    if code_col_i_index and col_h_letter:
                        formula_i = f'=IF(ISERROR(VLOOKUP({col_h_letter}{current_row},项目参考表!A:B,2,FALSE)),"",VLOOKUP({col_h_letter}{current_row},项目参考表!A:B,2,FALSE))'
                        sheet.Cells(current_row, code_col_i_index).Formula = formula_i

                workbook.Close(SaveChanges=True)
                excel.Quit()
                return len(records), None
            except Exception as e:
                if workbook: workbook.Close(SaveChanges=False)
                if excel: excel.Quit()
                return -1, str(e)
            finally:
                pythoncom.CoUninitialize()

        count, error = process_template_with_com(target_prescriptions, template_filename)
        if error:
            messagebox.showerror(f"导出失败", f"处理 '{template_filename}' 时发生错误：\n\n{error}")
        elif count > 0:
            messagebox.showinfo("导出成功", f"✔️ 成功追加 {count} 条药方记录到 '{template_filename}'")

    def run_diagnostics(self):
        """这是一个临时的诊断函数"""
        print("\n--- 开始诊断 ---")
        try:
            # 检查 self.doses_entry 是否存在且是一个有效的控件
            print(f"1. self.doses_entry 控件是: {self.doses_entry}")
            print(f"   - 控件的类是: {self.doses_entry.winfo_class()}")

            # 检查它绑定的 StringVar 变量
            # .cget() 方法可以获取控件的配置信息
            linked_var_name = self.doses_entry.cget("textvariable")
            print(f"2. 控件链接的变量名是: '{linked_var_name}'")

            # 直接从 StringVar 获取值
            current_var_value = self.doses_var.get()
            print(f"3. self.doses_var.get() 的当前值是: '{current_var_value}'")

            # 检查 _on_doses_changed 函数是否存在
            print(f"4. _on_doses_changed 函数是: {self._on_doses_changed}")

            print("--- 诊断结束 ---\n")

        except Exception as e:
            print(f"!!! 诊断过程中发生错误: {e} !!!")

    def _setup_focus_jumping(self):
        """
        [最终版] 设置焦点跳转，但完全忽略 teacher_entry 的回车键。
        """
        widgets = [
            self.teacher_entry,
            self.customer_entry,
            self.type_combobox,
            self.amount_entry,
            self.payment_combobox,
            self.channel_combobox,
            self.status_combobox,
            self.save_appointment_button
        ]

        for i, widget in enumerate(widgets[:-1]):
            next_widget = widgets[i + 1]

            def create_handler(next_w):
                def handler(event=None):
                    next_w.focus_set()
                    if isinstance(next_w, ttk.Combobox):
                        next_w.event_generate('<Button-1>')
                    return "break"

                return handler

            handler_func = create_handler(next_widget)

            # 关键修改：对 teacher_entry 不再绑定回车跳转
            if isinstance(widget, ttk.Entry) and widget != self.teacher_entry:
                widget.bind("<Return>", handler_func)
            elif isinstance(widget, ttk.Combobox):
                widget.bind("<<ComboboxSelected>>", handler_func)
                widget.bind("<Return>", handler_func)

        def save_and_focus_first(event=None):
            self._save_appointment()
            self.teacher_entry.focus_set()
            return "break"

        self.save_appointment_button.bind("<Return>", save_and_focus_first)

    def _create_appointment_widgets(self):
        """
        (V23 - 移除办卡充值付款方式版)
        1. 类型列表包含 [膏药]。
        2. 付款方式强制移除 [办卡充值] (因为它在类型里)。
        """
        self.appointment_frame.rowconfigure(0, weight=1)
        self.appointment_frame.columnconfigure(0, weight=1)

        main_frame = ttk.Frame(self.appointment_frame, padding="8")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # 1. 顶部筛选
        filter_frame = ttk.LabelFrame(main_frame, text=" 显示选项 ", padding=8)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        now = datetime.now()
        years = ['全部'] + list(range(now.year + 1, now.year - 5, -1))
        months = ['全部'] + [f"{i:02d}" for i in range(1, 13)]
        days = ['全部'] + [f"{i:02d}" for i in range(1, 32)]

        ttk.Label(filter_frame, text="年:").pack(side="left", padx=(0, 5))
        self.f_year = ttk.Combobox(filter_frame, values=years, width=7, state='readonly')
        self.f_year.pack(side="left")
        ttk.Label(filter_frame, text="月:").pack(side="left", padx=(10, 5))
        self.f_month = ttk.Combobox(filter_frame, values=months, width=5, state='readonly')
        self.f_month.pack(side="left")
        ttk.Label(filter_frame, text="日:").pack(side="left", padx=(10, 5))
        self.f_day = ttk.Combobox(filter_frame, values=days, width=5, state='readonly')
        self.f_day.pack(side="left")

        self.appt_total_var = tk.StringVar(value="总金额: 0.00 元")
        ttk.Label(filter_frame, textvariable=self.appt_total_var,
                  font=("Microsoft YaHei", 12, "bold"), foreground="blue").pack(side="right", padx=10)

        self.f_year.set('全部');
        self.f_month.set('全部');
        self.f_day.set('全部')
        self.f_year.bind("<<ComboboxSelected>>", self._populate_appointment_treeview)
        self.f_month.bind("<<ComboboxSelected>>", self._populate_appointment_treeview)
        self.f_day.bind("<<ComboboxSelected>>", self._populate_appointment_treeview)

        # 2. 列表区
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        cols = ("date", "time", "teacher", "customer", "type", "amount", "payment", "channel", "status")
        self.appointment_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        headings = {"date": "日期", "time": "时间", "teacher": "医师/销售", "customer": "客户/摘要", "type": "类型",
                    "amount": "金额", "payment": "付款方式", "channel": "渠道", "status": "是否完成"}
        for col, head in headings.items(): self.appointment_tree.heading(col, text=head)
        for col, width in {"date": 100, "time": 60, "teacher": 100, "customer": 120, "type": 80, "amount": 70,
                           "payment": 80, "channel": 60, "status": 60}.items():
            self.appointment_tree.column(col, width=width, anchor='center')

        vsb_appt = ttk.Scrollbar(tree_frame, orient="vertical", command=self.appointment_tree.yview)
        hsb_appt = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.appointment_tree.xview)
        self.appointment_tree.configure(yscrollcommand=vsb_appt.set, xscrollcommand=hsb_appt.set)
        self.appointment_tree.grid(row=0, column=0, sticky="nsew")
        vsb_appt.grid(row=0, column=1, sticky="ns")
        hsb_appt.grid(row=1, column=0, sticky="ew")
        self.appointment_tree.bind("<Double-1>", self._load_appointment_for_edit)

        # 3. 录入区
        input_frame = ttk.LabelFrame(main_frame, text=" 营业信息录入 ", padding=8)
        input_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_frame.columnconfigure((1, 3, 5), weight=1)

        # Row 0
        ttk.Label(input_frame, text="日期:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        date_frame = ttk.Frame(input_frame)
        date_frame.grid(row=0, column=1, sticky="ew")
        self.year_combo = ttk.Combobox(date_frame, values=years[1:], width=5, state='readonly')
        self.year_combo.pack(side="left", fill="x", expand=True)
        self.month_combo = ttk.Combobox(date_frame, values=months[1:], width=3, state='readonly')
        self.month_combo.pack(side="left", fill="x", expand=True, padx=1)
        self.day_combo = ttk.Combobox(date_frame, values=days[1:], width=3, state='readonly')
        self.day_combo.pack(side="left", fill="x", expand=True)

        ttk.Label(input_frame, text="时间:").grid(row=0, column=2, sticky="w", padx=(10, 5), pady=2)
        time_frame = ttk.Frame(input_frame)
        time_frame.grid(row=0, column=3, sticky="ew")
        self.hour_combo = ttk.Combobox(time_frame, values=[f"{h:02d}" for h in range(24)], width=3, state='readonly')
        self.hour_combo.pack(side="left", fill="x", expand=True)
        ttk.Label(time_frame, text=":").pack(side="left")
        self.minute_combo = ttk.Combobox(time_frame, values=[f"{m:02d}" for m in range(0, 60, 5)], width=3,
                                         state='readonly')
        self.minute_combo.pack(side="left", fill="x", expand=True)

        self.year_combo.set(str(now.year));
        self.month_combo.set(f"{now.month:02d}");
        self.day_combo.set(f"{now.day:02d}")
        self.hour_combo.set(f"{now.hour:02d}");
        self.minute_combo.set("00")

        ttk.Label(input_frame, text="类型:").grid(row=0, column=4, sticky="w", padx=(10, 5), pady=2)
        self.all_appt_types = [
            "中医", "理疗", "办卡充值",
            "中药", "合作收入",
            "茶包", "足浴包", "膏药",
            "大膏药", "解酒饮"
        ]
        self.type_combobox = ttk.Combobox(input_frame, state='readonly', values=self.all_appt_types)
        self.type_combobox.grid(row=0, column=5, sticky="ew")
        self.type_combobox.bind("<<ComboboxSelected>>", self._on_type_selected)

        # Row 1
        ttk.Label(input_frame, text="客户/摘要:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.customer_var = tk.StringVar()
        self.customer_entry = ttk.Entry(input_frame, textvariable=self.customer_var)
        self.customer_entry.grid(row=1, column=1, sticky="ew")

        ttk.Label(input_frame, text="医师/销售:").grid(row=1, column=2, sticky="w", padx=(10, 5), pady=2)
        teacher_frame = ttk.Frame(input_frame)
        teacher_frame.grid(row=1, column=3, sticky="ew")
        teacher_frame.columnconfigure(0, weight=1)
        self.teacher_var = tk.StringVar()
        self.teacher_entry = ttk.Entry(teacher_frame, textvariable=self.teacher_var)
        self.teacher_entry.grid(row=0, column=0, sticky="ew")
        self.teacher_results_listbox = tk.Listbox(teacher_frame, height=4, font=("Microsoft YaHei", 9))

        ttk.Label(input_frame, text="金额:").grid(row=1, column=4, sticky="w", padx=(10, 5), pady=2)
        self.amount_entry = ttk.Entry(input_frame)
        self.amount_entry.grid(row=1, column=5, sticky="ew")

        # Row 2
        ttk.Label(input_frame, text="付款方式:").grid(row=2, column=0, sticky="w", padx=5, pady=2)

        # ▼▼▼ 核心修改：移除 [医保账户] 和 [办卡充值] ▼▼▼
        loaded_methods = self.all_data['config_data'].get('payment_methods', [])
        base_methods = set(loaded_methods)
        base_methods.add("美团");
        base_methods.add("小红书")

        # 移除不需要的项
        for unwanted in ["医保账户", "办卡充值"]:
            if unwanted in base_methods:
                base_methods.remove(unwanted)

        final_methods = sorted(list(base_methods))
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        self.payment_combobox = ttk.Combobox(input_frame, values=final_methods, state='readonly')
        self.payment_combobox.grid(row=2, column=1, sticky="ew")
        self.payment_combobox.bind("<<ComboboxSelected>>", self._on_payment_method_selected)

        ttk.Label(input_frame, text="渠道:").grid(row=2, column=2, sticky="w", padx=(10, 5), pady=2)
        self.channel_combobox = ttk.Combobox(input_frame, values=["银行", "现金", "无"], state='disabled')
        self.channel_combobox.grid(row=2, column=3, sticky="ew")

        ttk.Label(input_frame, text="是否完成:").grid(row=2, column=4, sticky="w", padx=(10, 5), pady=2)
        self.status_combobox = ttk.Combobox(input_frame, values=["是", "否"], state='readonly')
        self.status_combobox.set("是")
        self.status_combobox.grid(row=2, column=5, sticky="ew")

        # 4. Buttons
        self.appointment_btn_frame = ttk.Frame(main_frame)
        self.appointment_btn_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        self.save_appointment_button = ttk.Button(self.appointment_btn_frame, text="保存",
                                                  command=self._save_appointment)
        self.save_appointment_button.pack(side="left", fill="x", expand=True, padx=2)

        self.find_appointment_button = ttk.Button(self.appointment_btn_frame, text="查找记录",
                                                  command=self.open_appointment_find_dialog)
        self.find_appointment_button.pack(side="left", fill="x", expand=True, padx=2)

        self.export_appointments_button = ttk.Button(self.appointment_btn_frame, text="导出Excel",
                                                     command=self.export_appointments)
        self.export_appointments_button.pack(side="left", fill="x", expand=True, padx=2)

        self.export_lemon_button = ttk.Button(self.appointment_btn_frame, text="导入柠檬云",
                                              command=self.export_for_lemon_cloud)
        self.export_lemon_button.pack(side="left", fill="x", expand=True, padx=2)

        self.clear_fields_button = ttk.Button(self.appointment_btn_frame, text="清空表单",
                                              command=self._clear_appointment_fields)
        self.clear_fields_button.pack(side="left", fill="x", expand=True, padx=2)

        self.delete_appointment_button = ttk.Button(self.appointment_btn_frame, text="删除选中",
                                                    command=self._delete_appointment)
        self.delete_appointment_button.pack(side="left", fill="x", expand=True, padx=2)

        self._bind_appointment_events()
        self._populate_appointment_treeview()
        if hasattr(self, '_setup_focus_jumping'): self._setup_focus_jumping()
    def _populate_user_treeview(self):
        """刷新用户列表，现在也显示管理员"""
        self.user_tree.delete(*self.user_tree.get_children())
        sorted_users = sorted(self.all_data.get('user_accounts', {}).items())
        for username, data in sorted_users:
            # 现在所有用户都显示
            self.user_tree.insert("", "end", values=(username, data.get('role_name', '')))

    def _create_menu(self):
        """创建顶部菜单栏"""
        if self.is_admin_view:
            return

        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        system_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="系统", menu=system_menu)

        system_menu.add_command(label="切换账号", command=self._request_logout)
        system_menu.add_separator()

        # ▼▼▼ 更新这里的函数调用 ▼▼▼
        system_menu.add_command(label="退出程序", command=self._on_window_close)
        # ▲▲▲ 更新结束 ▲▲▲

    def _request_logout(self):
        """请求注销并返回登录界面"""
        if messagebox.askokcancel("确认", "您确定要切换账号吗？所有未保存的数据将丢失。"):
            self.logout_request = True
            self.root.destroy()

    def export_appointments(self):
        import pandas as pd
        self._rebuild_view_lists()
        current_iids = self.appointment_tree.get_children()
        appointments_in_view = [a for a in self.view_appointments if a['id'] in current_iids]

        if not appointments_in_view:
            messagebox.showinfo("提示", "当前列表没有预约记录可导出。")
            return

        display_fields = {
            'date': {'label': '日期'},
            'customer': {'label': '客户'},
            'teacher': {'label': '医师'},
            'type': {'label': '类型'}
        }

        dialog = AdvancedFilterDialog(self.root, "请勾选要导出的预约记录", appointments_in_view, display_fields)
        channel_frame = ttk.Frame(dialog.main_frame)
        # 将新控件放置在按钮框架之前
        channel_frame.pack(fill="x", pady=5, before=dialog.btn_frame)
        ttk.Label(channel_frame, text="导出渠道:").pack(side="left")
        channel_var = tk.StringVar(value="银行")
        ttk.Combobox(channel_frame, textvariable=channel_var, values=["银行", "现金"], state="readonly").pack(
            side="left", padx=5)
        dialog.extra_widgets['channel'] = channel_var

        selected_ids = dialog.show()

        if selected_ids is None: return

        target_appointments = [a for a in appointments_in_view if a.get('id') in selected_ids]
        if not target_appointments:
            messagebox.showinfo("提示", "没有选中任何有效的预约记录。")
            return

        # --- Pandas 导出逻辑 ---
        can_include_amount = self.permissions.get('export_appt_include_amount', False)
        can_include_commission = self.permissions.get('export_appt_include_commission', False)
        df_commission = None;
        teachers_in_this_export = []

        if can_include_commission:
            df_commission = self.all_data['config_data'].get('commission_rules')
            if df_commission is None or df_commission.empty:
                can_include_commission = False
            else:
                teachers_in_this_export = sorted(list(set(
                    rec.get('teacher', '').strip() for rec in target_appointments if rec.get('teacher', '').strip())))

        export_data = [];
        has_calculation_errors = False
        for record in target_appointments:
            row_data = {
                '日期': record.get('date', ''), '时间': f"{record.get('hour', '')}:{record.get('minute', '')}",
                '老师': record.get('teacher', ''), '客户': record.get('customer', ''),
                '服务类型': record.get('type', ''),
                '付款方式': record.get('payment', ''), '渠道': record.get('channel', ''),
                '完成状态': record.get('status', '')
            }
            if can_include_amount: row_data['金额'] = record.get('amount', '')

            if can_include_commission and df_commission is not None:
                commission_rate, commission_amount, remarks = 0.0, 0.0, []
                teacher = record.get('teacher', '').strip()
                service_type = record.get('type', '').strip()
                try:
                    amount = float(record.get('amount', 0))
                except (ValueError, TypeError):
                    amount = 0.0

                # ▼▼▼▼▼ 核心修改 2：扩展提成计算逻辑 ▼▼▼▼▼
                payment_method = record.get('payment', '').strip()
                if payment_method == "办卡充值":
                    lookup_service_type = "办卡充值"
                else:
                    lookup_service_type = service_type

                teacher_found = teacher in df_commission.index
                type_found = lookup_service_type in df_commission.columns
                # ▲▲▲▲▲ 修改结束 ▲▲▲▲▲

                if not teacher_found: remarks.append(f"老师'{teacher}'未在提成表找到;")
                if not type_found: remarks.append(f"服务'{lookup_service_type}'未在提成表找到;")
                if teacher_found and type_found:
                    try:
                        rate_value = df_commission.loc[teacher, lookup_service_type]
                        if pd.notna(rate_value):
                            commission_rate = float(rate_value);
                            commission_amount = amount * commission_rate
                        else:
                            remarks.append("比例单元格为空;")
                    except Exception:
                        remarks.append("比例值非数字;")
                if remarks: has_calculation_errors = True
                row_data['提成比例'] = commission_rate if commission_rate > 0 else ''
                row_data['备注'] = " ".join(remarks)
                teacher_commission_cols = {t_name: '' for t_name in teachers_in_this_export}
                if commission_amount > 0 and teacher in teacher_commission_cols:
                    teacher_commission_cols[teacher] = f"{commission_amount:.2f}"
                row_data.update(teacher_commission_cols)
            export_data.append(row_data)

        try:
            filename = filedialog.asksaveasfilename(title="保存记录", defaultextension=".xlsx",
                                                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
            if filename:
                import pandas as pd
                df_export = pd.DataFrame(export_data)
                base_columns = ['日期', '时间', '老师', '客户', '服务类型', '付款方式', '渠道', '完成状态']
                final_column_order = base_columns[:]
                insert_pos = 5
                if can_include_amount: final_column_order.insert(insert_pos, '金额'); insert_pos += 1
                if can_include_commission:
                    final_column_order.insert(insert_pos, '提成比例')
                    final_column_order.extend(['备注'] + teachers_in_this_export)
                df_export = df_export.reindex(columns=final_column_order)
                df_export.to_excel(filename, index=False, sheet_name='预约记录')
                success_message = f"已成功导出 {len(target_appointments)} 条勾选的预约记录到文件：\n{filename}"
                if has_calculation_errors:
                    messagebox.showwarning("导出警告",
                                           f"{success_message}\n\n但部分记录的提成计算失败。\n请查看'备注'列了解原因。")
                else:
                    messagebox.showinfo("成功", success_message)
        except Exception as e:
            messagebox.showerror("导出失败", f"导出过程中出现错误：\n{str(e)}")

    def open_commission_summary_window(self):
        """(仅管理员) (V2 - 使用缓存) 打开一个详细的提成统计窗口"""
        import pandas as pd
        current_iids = self.appointment_tree.get_children()
        if not current_iids:
            messagebox.showinfo("提示", "当前列表没有记录，无法进行提成统计。")
            return

        # --- 核心修改：直接从缓存中获取提成规则 ---
        df_commission = self.all_data['config_data'].get('commission_rules')
        if df_commission is None or df_commission.empty:
            messagebox.showerror("提成规则缺失", "未能加载提成规则数据。\n请确保 commissionRate.csv 曾被成功加载过。")
            return

        appointments_in_view = [record for record in self.current_user_appointments if
                                record['id'] in current_iids]

        # --- 创建新窗口 ---
        summary_win = tk.Toplevel(self.root)
        summary_win.title("提成明细与汇总")
        summary_win.geometry("800x500")
        summary_win.transient(self.root)
        summary_win.grab_set()

        main_frame = ttk.Frame(summary_win, padding=10)
        main_frame.pack(fill="both", expand=True)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # ... (后续所有创建 Treeview 和计算的代码都与之前版本相同，是正确的)
        cols = ("date", "teacher", "customer", "type", "amount", "rate", "commission")
        tree = ttk.Treeview(main_frame, columns=cols, show='headings')
        tree.heading("date", text="日期");
        tree.heading("teacher", text="老师");
        tree.heading("customer", text="客户");
        tree.heading("type", text="服务类型");
        tree.heading("amount", text="项目金额");
        tree.heading("rate", text="提成比例");
        tree.heading("commission", text="提成金额")
        tree.column("date", anchor='center', width=100);
        tree.column("teacher", anchor='center', width=100);
        tree.column("customer", anchor='w', width=120);
        tree.column("type", anchor='center', width=80);
        tree.column("amount", anchor='e', width=90);
        tree.column("rate", anchor='center', width=80);
        tree.column("commission", anchor='e', width=90)
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview);
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew");
        vsb.grid(row=0, column=1, sticky="ns")

        teacher_summary = {};
        total_commission_overall = 0.0
        sorted_appointments = sorted(appointments_in_view, key=lambda x: (x.get('date', ''), x.get('teacher', '')))
        for record in sorted_appointments:
            teacher = record.get('teacher', '').strip()
            if not teacher: continue
            service_type = record.get('type', '').strip()
            try:
                amount = float(record.get('amount', 0))
            except (ValueError, TypeError):
                amount = 0.0
            rate_value = 0.0;
            commission_amount = 0.0
            if teacher in df_commission.index and service_type in df_commission.columns:
                try:
                    rate_from_file = df_commission.loc[teacher, service_type]
                    if pd.notna(rate_from_file):
                        rate_value = float(rate_from_file)
                        commission_amount = amount * rate_value
                except (ValueError, TypeError):
                    pass
            tree.insert("", "end", values=(
                record.get('date', ''), teacher, record.get('customer', ''), service_type, f"{amount:.2f}",
                f"{rate_value:.2%}" if rate_value > 0 else "0.00%", f"{commission_amount:.2f}"))
            teacher_summary.setdefault(teacher, 0.0);
            teacher_summary[teacher] += commission_amount;
            total_commission_overall += commission_amount

        summary_frame = ttk.LabelFrame(main_frame, text="各老师提成汇总", padding=10)
        summary_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        summary_cols = ("teacher", "total");
        summary_tree = ttk.Treeview(summary_frame, columns=summary_cols, show='headings', height=5)
        summary_tree.heading("teacher", text="老师姓名");
        summary_tree.heading("total", text="提成总金额 (元)")
        summary_tree.column("teacher", anchor='center', width=150);
        summary_tree.column("total", anchor='e', width=150)
        sorted_summary = sorted(teacher_summary.items(), key=lambda item: item[1], reverse=True)
        for teacher, total in sorted_summary:
            if total > 0: summary_tree.insert("", "end", values=(teacher, f"{total:.2f}"))
        summary_tree.pack(side="left", fill="both", expand=True)

        total_frame = ttk.Frame(summary_frame, padding=(10, 0, 0, 0));
        total_frame.pack(side="left", fill="y")
        ttk.Label(total_frame, text="合计总提成:", font=("Microsoft YaHei", 11, "bold")).pack(anchor='n', pady=5)
        ttk.Label(total_frame, text=f"{total_commission_overall:.2f} 元", font=("Microsoft YaHei", 12, "bold"),
                  foreground="blue").pack(anchor='n')

    def _create_commission_widgets(self):
        """(仅管理员) 创建提成统计页面的所有控件"""
        main_frame = ttk.Frame(self.commission_frame, padding=10)
        main_frame.pack(fill="both", expand=True)
        main_frame.rowconfigure(1, weight=1)  # 为列表区设置权重
        main_frame.columnconfigure(0, weight=1)  # 为列表区设置权重

        # --- 1. 顶部的过滤器和操作按钮 ---
        filter_frame = ttk.LabelFrame(main_frame, text=" 筛选与操作 ", padding=8)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # (这里的日期过滤器代码和信息登记页的完全一样)
        now = datetime.now()
        years = ['全部'] + list(range(now.year + 1, now.year - 5, -1))
        months = ['全部'] + [f"{i:02d}" for i in range(1, 13)]
        days = ['全部'] + [f"{i:02d}" for i in range(1, 32)]
        ttk.Label(filter_frame, text="年:").pack(side="left", padx=(0, 5))
        self.c_year = ttk.Combobox(filter_frame, values=years, width=7, state='readonly')
        self.c_year.pack(side="left")
        ttk.Label(filter_frame, text="月:").pack(side="left", padx=(10, 5))
        self.c_month = ttk.Combobox(filter_frame, values=months, width=5, state='readonly')
        self.c_month.pack(side="left")
        ttk.Label(filter_frame, text="日:").pack(side="left", padx=(10, 5))
        self.c_day = ttk.Combobox(filter_frame, values=days, width=5, state='readonly')
        self.c_day.pack(side="left")
        self.c_year.set(str(now.year))  # 默认显示当年
        self.c_month.set(f"{now.month:02d}")  # 默认显示当月
        self.c_day.set('全部')

        # 刷新按钮
        self.refresh_commission_button = ttk.Button(filter_frame, text="刷新统计",
                                                    command=self._populate_commission_treeview)
        self.refresh_commission_button.pack(side="right", padx=(20, 0))

        # 绑定事件
        self.c_year.bind("<<ComboboxSelected>>", self._populate_commission_treeview)
        self.c_month.bind("<<ComboboxSelected>>", self._populate_commission_treeview)
        self.c_day.bind("<<ComboboxSelected>>", self._populate_commission_treeview)

        # --- 2. 中间的详细信息列表 ---
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        cols = ("date", "teacher", "customer", "type", "amount", "rate", "commission")
        self.commission_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        self.commission_tree.heading("date", text="日期")
        self.commission_tree.heading("teacher", text="老师")
        self.commission_tree.heading("customer", text="客户")
        self.commission_tree.heading("type", text="服务类型")
        self.commission_tree.heading("amount", text="项目金额")
        self.commission_tree.heading("rate", text="提成比例")
        self.commission_tree.heading("commission", text="提成金额")

        for col, width, anchor in [("date", 100, 'center'), ("teacher", 100, 'center'),
                                   ("customer", 120, 'center'), ("type", 80, 'center'),
                                   ("amount", 90, 'center'), ("rate", 80, 'center'),
                                   ("commission", 90, 'center')]:
            self.commission_tree.column(col, anchor=anchor, width=width)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.commission_tree.yview)
        self.commission_tree.configure(yscrollcommand=vsb.set)
        self.commission_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # --- 3. 底部的汇总区域 ---
        summary_frame = ttk.LabelFrame(main_frame, text="各老师提成汇总", padding=10)
        summary_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        summary_frame.rowconfigure(0, weight=1)
        summary_frame.columnconfigure(0, weight=1)

        summary_cols = ("teacher", "total")
        self.commission_summary_tree = ttk.Treeview(summary_frame, columns=summary_cols, show='headings', height=6)
        self.commission_summary_tree.heading("teacher", text="老师姓名")
        self.commission_summary_tree.heading("total", text="提成总金额 (元)")
        self.commission_summary_tree.column("teacher", anchor='center', width=200)
        self.commission_summary_tree.column("total", anchor='center', width=200)

        summary_vsb = ttk.Scrollbar(summary_frame, orient="vertical", command=self.commission_summary_tree.yview)
        self.commission_summary_tree.configure(yscrollcommand=summary_vsb.set)
        self.commission_summary_tree.grid(row=0, column=0, sticky="nsew")
        summary_vsb.grid(row=0, column=1, sticky="ns")

    def _populate_commission_treeview(self, event=None):
        """
        (V5 - 美团九折提成版)
        逻辑更新：
        如果付款方式是 [美团]，计算提成时，金额基数先打9折。
        即：提成 = (金额 * 0.9) * 比例。
        """
        self._rebuild_view_lists()
        import pandas as pd
        self.commission_tree.delete(*self.commission_tree.get_children())
        self.commission_summary_tree.delete(*self.commission_summary_tree.get_children())

        df_commission = self.all_data['config_data'].get('commission_rules')

        y = self.c_year.get()
        m = self.c_month.get()
        d = self.c_day.get()

        appointments = self.view_appointments
        filtered_appointments = []
        for record in appointments:
            date_str = record.get('date', '')
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                continue
            match = (y == '全部' or str(date_obj.year) == y) and \
                    (m == '全部' or f"{date_obj.month:02d}" == m) and \
                    (d == '全部' or f"{date_obj.day:02d}" == d)
            if match: filtered_appointments.append(record)

        if not filtered_appointments: return

        teacher_summary = {}
        # 按日期和老师排序
        for record in sorted(filtered_appointments, key=lambda x: (x.get('date', ''), x.get('teacher', ''))):
            teacher = record.get('teacher', '').strip()
            # 过滤无效老师 (中药销售/合作收入等无提成项目)
            if teacher in ["无", "未指定", ""] or not teacher: continue

            service_type = record.get('type', '').strip()
            payment_method = record.get('payment', '').strip()

            # 1. 获取原始金额
            try:
                raw_amount = float(record.get('amount', 0))
            except:
                raw_amount = 0.0

            # ▼▼▼ 2. 核心修改：美团提成基数打9折 ▼▼▼
            if payment_method == "美团":
                calc_base = raw_amount * 0.9
            else:
                calc_base = raw_amount
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

            rate_value = 0.0
            commission_amount = 0.0
            extra_rows = []

            # --- 3. 计算提成 (使用 calc_base) ---

            # A. 茶包 (固定 5%)
            if service_type == "茶包":
                rate_value = 0.05
                commission_amount = calc_base * rate_value

            # B. 足浴包 (销售 5% + 李福兴 15%)
            elif service_type == "足浴包":
                # 销售人员
                rate_value = 0.05
                commission_amount = calc_base * rate_value

                # 李福兴分润
                lfx_amount = calc_base * 0.15
                extra_rows.append({
                    "teacher": "李福兴",
                    "type": "足浴包(分润)",
                    "rate": 0.15,
                    "commission": lfx_amount
                })

            # C. 办卡充值 (固定 5%)
            elif service_type == "办卡充值":
                lookup_type = "办卡充值"
                # 优先查表，查不到默认0.05
                if df_commission is not None and teacher in df_commission.index and lookup_type in df_commission.columns:
                    rate = df_commission.loc[teacher, lookup_type]
                    if pd.notna(rate):
                        rate_value = float(rate)
                    else:
                        rate_value = 0.05
                else:
                    rate_value = 0.05

                commission_amount = calc_base * rate_value

            # D. 常规 (中医、理疗、出药、大膏药、解酒饮)
            else:
                # 查找 CSV 规则
                if df_commission is not None and teacher in df_commission.index and service_type in df_commission.columns:
                    try:
                        rate = df_commission.loc[teacher, service_type]
                        if pd.notna(rate):
                            rate_value = float(rate)
                            commission_amount = calc_base * rate_value
                    except:
                        pass

            # --- 4. 插入列表 ---
            # 注意：列表显示的【项目金额】依然是 raw_amount (原始金额)，但【提成金额】是按打折后算的
            self.commission_tree.insert("", "end", values=(
                record.get('date', ''),
                teacher,
                record.get('customer', ''),
                service_type,
                f"{raw_amount:.2f}",  # 显示原始金额
                f"{rate_value:.2%}",
                f"{commission_amount:.2f}"  # 显示打折后计算的提成
            ))

            teacher_summary.setdefault(teacher, 0.0)
            teacher_summary[teacher] += commission_amount

            # 插入额外行
            for ex in extra_rows:
                self.commission_tree.insert("", "end", values=(
                    record.get('date', ''),
                    ex['teacher'],
                    f"({record.get('customer', '')})",
                    ex['type'],
                    "-",  # 分润行不显示项目金额，避免误解
                    f"{ex['rate']:.2%}",
                    f"{ex['commission']:.2f}"
                ))
                teacher_summary.setdefault(ex['teacher'], 0.0)
                teacher_summary[ex['teacher']] += ex['commission']

        # 刷新右下角汇总
        for teacher, total in sorted(teacher_summary.items(), key=lambda item: item[1], reverse=True):
            if total > 0:
                self.commission_summary_tree.insert("", "end", values=(teacher, f"{total:.2f}"))
    def _create_expense_widgets(self):
        """
        (V8 - 变量名修正版)
        确保保存按钮变量名为 self.exp_save_button
        """
        self.editing_expense_id = None
        self.expense_frame.rowconfigure(0, weight=1)
        self.expense_frame.columnconfigure(0, weight=1)

        main_frame = ttk.Frame(self.expense_frame, padding="8")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # 1. 顶部统计
        stats_frame = ttk.LabelFrame(main_frame, text=" 统计信息 ", padding=8)
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.exp_total_var = tk.StringVar(value="总支出: 0.00 元")
        ttk.Label(stats_frame, textvariable=self.exp_total_var,
                  font=("Microsoft YaHei", 12, "bold"), foreground="red").pack(side="right", padx=10)
        ttk.Label(stats_frame, text="当前列表统计:").pack(side="right")

        # 2. 录入区
        input_frame = ttk.LabelFramde(main_frame, text=" 登记/修改支出 ", padding=8)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        input_frame.columnconfigure((1, 3), weight=1)

        ttk.Label(input_frame, text="日期:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.exp_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ttk.Entry(input_frame, textvariable=self.exp_date_var).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(input_frame, text="支出类型:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.exp_type_var = tk.StringVar()
        expense_types = [
            "购买材料", "工资社保", "税费支出", "个人所得税",
            "利息支出", "手续费", "租金物业", "水电费",
            "运输费", "差旅费", "招待费", "其他支出",
            "装修款", "采购材料", "煎药费", "员工餐费",
            "业务退款", "运营相关费用", "员工福利费",
            "租金物业1", "应收款"
        ]
        ttk.Combobox(input_frame, textvariable=self.exp_type_var, values=expense_types, state='readonly').grid(row=0,
                                                                                                               column=3,
                                                                                                               sticky="ew",
                                                                                                               padx=5)

        ttk.Label(input_frame, text="摘要:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.exp_summary_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.exp_summary_var).grid(row=1, column=1, sticky="ew", padx=5)

        ttk.Label(input_frame, text="金额:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.exp_amount_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.exp_amount_var).grid(row=1, column=3, sticky="ew", padx=5)

        ttk.Label(input_frame, text="付款方式:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.exp_payment_var = tk.StringVar()
        ttk.Combobox(input_frame, textvariable=self.exp_payment_var, values=["现金", "银行"], state='readonly').grid(
            row=2, column=1, sticky="ew", padx=5)

        # 3. 列表区
        tree_frame = ttk.LabelFrame(main_frame, text=" 支出记录列表 (双击修改) ", padding=8)
        tree_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        cols = ("date", "type", "summary", "payment", "amount")
        self.expense_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        headings = {"date": "日期", "type": "支出类型", "summary": "摘要", "payment": "付款方式", "amount": "金额"}
        for col, text in headings.items():
            self.expense_tree.heading(col, text=text)
            self.expense_tree.column(col, anchor='center', width=100)
        self.expense_tree.column("summary", width=250, anchor='center')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=vsb.set)
        self.expense_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.expense_tree.bind("<Double-1>", self._load_expense_for_edit)

        # 4. 按钮区
        self.expense_btn_frame = ttk.Frame(main_frame)
        self.expense_btn_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        # ▼▼▼ 统一名称为 self.exp_save_button ▼▼▼
        self.exp_save_button = ttk.Button(self.expense_btn_frame, text="保存支出", command=self._save_expense)
        self.exp_save_button.pack(side="left", fill="x", expand=True, padx=2)

        self.exp_export_excel_button = ttk.Button(self.expense_btn_frame, text="导出Excel",
                                                  command=self.export_expenses_excel)
        self.exp_export_excel_button.pack(side="left", fill="x", expand=True, padx=2)

        self.exp_export_lemon_button = ttk.Button(self.expense_btn_frame, text="导入柠檬云",
                                                  command=self.export_expenses_lemon_cloud)
        self.exp_export_lemon_button.pack(side="left", fill="x", expand=True, padx=2)

        self.exp_clear_button = ttk.Button(self.expense_btn_frame, text="清空表单", command=self._clear_expense_form)
        self.exp_clear_button.pack(side="left", fill="x", expand=True, padx=2)

        self.exp_delete_button = ttk.Button(self.expense_btn_frame, text="删除选中", command=self._delete_expense)
        self.exp_delete_button.pack(side="left", fill="x", expand=True, padx=2)

        self._populate_expense_tree()

    def _load_expense_for_edit(self, event):
        """双击加载支出记录"""
        selected_iid = self.expense_tree.focus()
        if not selected_iid: return

        record = next((r for r in self.current_user_expenses if r['id'] == selected_iid), None)

        if record:
            self.editing_expense_id = selected_iid

            self.exp_date_var.set(record.get('date', ''))
            self.exp_type_var.set(record.get('type', ''))
            self.exp_summary_var.set(record.get('summary', ''))
            self.exp_amount_var.set(record.get('amount', ''))
            self.exp_payment_var.set(record.get('payment', ''))

            # ▼▼▼ 修正引用名 ▼▼▼
            self.exp_save_button.config(text="更新支出")
    def _save_expense(self):
        """保存或更新支出记录"""
        # 1. 基础校验
        if not all([self.exp_date_var.get(), self.exp_type_var.get(), self.exp_amount_var.get()]):
            messagebox.showerror("错误", "日期、类型和金额为必填项！");
            return

        try:
            float(self.exp_amount_var.get())
        except ValueError:
            messagebox.showerror("错误", "金额格式不正确！");
            return

        # 2. 构建数据包
        data = {
            "date": self.exp_date_var.get().strip(),
            "type": self.exp_type_var.get().strip(),
            "summary": self.exp_summary_var.get().strip(),
            "payment": self.exp_payment_var.get().strip(),
            "amount": self.exp_amount_var.get().strip()
        }

        # 3. 判断是更新还是新增
        if self.editing_expense_id:
            # --- 更新模式 ---
            # 保持ID不变
            data['id'] = self.editing_expense_id

            # 找到并在列表中替换
            found = False
            for i, record in enumerate(self.current_user_expenses):
                if record['id'] == self.editing_expense_id:
                    self.current_user_expenses[i] = data
                    found = True
                    break
            if not found:
                # 极少情况：编辑时ID丢失，当作新增
                self.current_user_expenses.append(data)

            msg = "支出记录已更新"
        else:
            # --- 新增模式 ---
            data['id'] = datetime.now().isoformat()
            self.current_user_expenses.append(data)
            msg = "支出记录已保存"

        # 4. 保存并刷新
        self._save_database()
        self._populate_expense_tree()
        self._clear_expense_form()  # 保存后自动清空
        messagebox.showinfo("成功", msg)

    def _clear_expense_form(self):
        """清空支出表单"""
        self.editing_expense_id = None
        self.exp_date_var.set(datetime.now().strftime('%Y-%m-%d'))
        self.exp_type_var.set('')
        self.exp_summary_var.set('')
        self.exp_amount_var.set('')
        self.exp_payment_var.set('')

        # ▼▼▼ 修正引用名 ▼▼▼
        self.exp_save_button.config(text="保存支出")

        if self.expense_tree.selection():
            self.expense_tree.selection_remove(self.expense_tree.selection())
    def _delete_expense(self):
        sel = self.expense_tree.selection()
        if not sel: return
        if messagebox.askyesno("确认", "删除选中记录？"):
            # 根据值匹配删除（因为treeview的iid不一定等于id，这里简化处理，若有id最好用id）
            # 假设插入时没指定iid，treeview自动生成。这里简单重刷列表
            # 更好的做法是在populate时绑定iid
            pass
            # 修正：
            items_to_del = []
            for iid in sel:
                vals = self.expense_tree.item(iid, 'values')
                # 这是一个简化的删除匹配，实际应该用ID。鉴于篇幅，这里假设populate使用了ID
                # 重新修改 populate

            # 正确逻辑：
            ids_to_del = set(sel)
            self.current_user_expenses[:] = [x for x in self.current_user_expenses if x['id'] not in ids_to_del]
            self._save_database()
            self._populate_expense_tree()

    def _populate_expense_tree(self):
        self.expense_tree.delete(*self.expense_tree.get_children())

        # 排序
        sorted_expenses = sorted(self.current_user_expenses, key=lambda x: x.get('date', ''), reverse=True)

        # ▼▼▼ 新增：计算总支出 ▼▼▼
        total_expense = 0.0

        for r in sorted_expenses:
            try:
                total_expense += float(r.get('amount', 0))
            except:
                pass

            self.expense_tree.insert("", "end", iid=r['id'], values=(
                r.get('date', ''),
                r.get('type', ''),
                r.get('summary', ''),
                r.get('payment', ''),
                r.get('amount', '')
            ))

        # 更新红色标签
        self.exp_total_var.set(f"总支出: {total_expense:.2f} 元")
    def open_appointment_find_dialog(self):
        appointments = self.current_user_appointments
        if not appointments:
            messagebox.showinfo("提示", "当前没有预约记录，无需查找。")
            return

        find_window = tk.Toplevel(self.root)
        find_window.title("查找预约记录")
        find_window.geometry("400x300")
        find_window.resizable(False, False)
        find_window.transient(self.root)
        find_window.grab_set()

        frame = ttk.Frame(find_window, padding=10)
        frame.pack(expand=True, fill="both")
        frame.columnconfigure(1, weight=1)

        # 查找条件
        ttk.Label(frame, text="客户姓名 (可留空):").grid(row=0, column=0, sticky="w", pady=2)
        customer_entry = ttk.Entry(frame)
        customer_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(5, 0))

        ttk.Label(frame, text="老师姓名 (可留空):").grid(row=1, column=0, sticky="w", pady=2)
        teacher_entry = ttk.Entry(frame)
        teacher_entry.grid(row=1, column=1, sticky="ew", pady=2, padx=(5, 0))

        ttk.Label(frame, text="服务类型 (可留空):").grid(row=2, column=0, sticky="w", pady=2)
        type_entry = ttk.Entry(frame)
        type_entry.grid(row=2, column=1, sticky="ew", pady=2, padx=(5, 0))

        ttk.Label(frame, text="日期 (YYYY-MM-DD, 可留空):").grid(row=3, column=0, sticky="w", pady=2)
        date_entry = ttk.Entry(frame)
        date_entry.grid(row=3, column=1, sticky="ew", pady=2, padx=(5, 0))

        ttk.Label(frame, text="金额 (可留空):").grid(row=4, column=0, sticky="w", pady=2)
        amount_entry = ttk.Entry(frame)
        amount_entry.grid(row=4, column=1, sticky="ew", pady=2, padx=(5, 0))

        ttk.Label(frame, text="完成状态:").grid(row=5, column=0, sticky="w", pady=2)
        status_var = tk.StringVar(master=find_window)
        status_combo = ttk.Combobox(frame, textvariable=status_var, values=["全部", "是", "否"], state='readonly')
        status_combo.set("全部")
        status_combo.grid(row=5, column=1, sticky="ew", pady=2, padx=(5, 0))

        def perform_search():
            customer_q = customer_entry.get().strip().lower()
            teacher_q = teacher_entry.get().strip().lower()
            type_q = type_entry.get().strip().lower()
            date_q = date_entry.get().strip()
            amount_q = amount_entry.get().strip()
            status_q = status_var.get()

            # 检查是否至少输入了一个查找条件
            if not any([customer_q, teacher_q, type_q, date_q, amount_q]) and status_q == "全部":
                messagebox.showwarning("输入错误", "请输入至少一个查找条件！", parent=find_window)
                return

            # 验证金额输入
            if amount_q:
                try:
                    float(amount_q)
                except ValueError:
                    messagebox.showerror("输入错误", "金额必须是有效的数字！", parent=find_window)
                    return

            found_iids = []
            for record in appointments:
                match = True

                # 检查客户姓名
                if customer_q and customer_q not in record.get('customer', '').lower():
                    match = False

                # 检查老师姓名
                if teacher_q and teacher_q not in record.get('teacher', '').lower():
                    match = False

                # 检查服务类型
                if type_q and type_q not in record.get('type', '').lower():
                    match = False

                # 检查日期
                if date_q and date_q not in record.get('date', ''):
                    match = False

                # 检查金额
                if amount_q:
                    try:
                        if float(amount_q) != float(record.get('amount', 0)):
                            match = False
                    except (ValueError, TypeError):
                        match = False

                # 检查完成状态
                if status_q != "全部" and status_q != record.get('status', ''):
                    match = False

                if match:
                    found_iids.append(record['id'])

            if found_iids:
                # 切换到信息登记标签页
                self.notebook.select(1)
                # 清空当前筛选条件以显示所有记录
                self.year_filter.set('全部')
                self.month_filter.set('全部')
                self.day_filter.set('全部')
                self._populate_appointment_treeview()
                # 选中找到的记录
                self.appointment_tree.selection_set(found_iids)
                if found_iids:
                    self.appointment_tree.see(found_iids[0])
                find_window.destroy()
                messagebox.showinfo("查找结果", f"找到 {len(found_iids)} 条匹配的预约记录。")
            else:
                messagebox.showinfo("未找到", "没有找到符合条件的预约记录。", parent=find_window)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="查 找", command=perform_search).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取 消", command=find_window.destroy).pack(side="left", padx=5)

        customer_entry.focus_set()
        # 绑定回车键执行查找
        for entry in [customer_entry, teacher_entry, type_entry, date_entry, amount_entry]:
            entry.bind("<Return>", lambda e: perform_search())

        self.root.wait_window(find_window)

    def _populate_appointment_treeview(self, event=None):
        self._rebuild_view_lists()
        self.appointment_tree.delete(*self.appointment_tree.get_children())

        y = self.f_year.get()
        m = self.f_month.get()
        d = self.f_day.get()

        appointments = self.view_appointments
        filtered = []
        for record in appointments:
            date_str = record.get('date', '')
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                continue

            match = True
            if y != '全部' and str(date_obj.year) != y: match = False
            if m != '全部' and f"{date_obj.month:02d}" != m: match = False
            if d != '全部' and f"{date_obj.day:02d}" != d: match = False

            if match: filtered.append(record)

        filtered.sort(key=lambda x: x.get('id', ''), reverse=True)

        # ▼▼▼ 新增：计算总金额 ▼▼▼
        total_amount = 0.0

        for record in filtered:
            # 累加
            try:
                total_amount += float(record.get('amount', 0))
            except:
                pass

            self.appointment_tree.insert("", "end", iid=record['id'], values=(
                record.get('date', ''), f"{record.get('hour', '')}:{record.get('minute', '')}",
                record.get('teacher', ''), record.get('customer', ''),
                record.get('type', ''), record.get('amount', ''),
                record.get('payment', ''), record.get('channel', ''),
                record.get('status', '')
            ))

        # 更新标签
        self.appt_total_var.set(f"总金额: {total_amount:.2f} 元")

    def _save_appointment(self):
        data = {
            "date": f"{self.year_combo.get()}-{self.month_combo.get()}-{self.day_combo.get()}",
            "hour": self.hour_combo.get(), "minute": self.minute_combo.get(),
            "teacher": self.teacher_entry.get().strip(),
            "customer": self.customer_entry.get().strip(),
            "type": self.type_combobox.get(),
            "amount": self.amount_entry.get(),
            "payment": self.payment_combobox.get(),
            "channel": self.channel_combobox.get(),
            "status": self.status_combobox.get()
        }

        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("输入错误", "日期无效！"); return

        if not data['type'] or not data['amount'] or not data['payment']:
            messagebox.showerror("输入错误", "类型、金额、付款方式为必填项！");
            return

        # ▼▼▼ 核心修改：只校验类型，因为付款方式里已经没办卡充值了 ▼▼▼
        if data['type'] == "办卡充值":
            if data['payment'] not in ["现金", "收钱吧"]:
                messagebox.showerror("规则错误", "【办卡充值】业务，付款方式必须是 [现金] 或 [收钱吧]！");
                return
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        try:
            if float(data['amount']) <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "金额必须大于0！"); return

        if data['type'] not in ["中药", "合作收入"]:
            if not data['teacher']:
                messagebox.showerror("输入错误", "请填写医师/销售人员姓名！");
                return
            official_teachers = self.all_data['config_data'].get('teachers', [])
            if data['teacher'] not in official_teachers:
                messagebox.showerror("输入错误", f"姓名 '{data['teacher']}' 不在官方列表中。")
                self.teacher_entry.focus_set();
                return
        else:
            data['teacher'] = "未指定"

        if self.editing_id:
            for i, record in enumerate(self.current_user_appointments):
                if record['id'] == self.editing_id:
                    self.current_user_appointments[i].update(data);
                    break
        else:
            data['id'] = datetime.now().isoformat()
            self.current_user_appointments.append(data)

        self._save_database()
        self._populate_appointment_treeview()
        self._clear_appointment_fields()
    def _load_appointment_for_edit(self, event):
        selected_iid = self.appointment_tree.focus()
        if not selected_iid:
            return

        # self.view_appointments 是动态更新的，从这里查找更安全
        record = next((p for p in self.view_appointments if p['id'] == selected_iid), None)

        if record:
            self.editing_id = selected_iid

            date_parts = record.get('date', '---').split('-')
            self.year_combo.set(date_parts[0])
            self.month_combo.set(date_parts[1])
            self.day_combo.set(date_parts[2])
            self.hour_combo.set(record.get('hour', ''))
            self.minute_combo.set(record.get('minute', ''))

            self.teacher_entry.delete(0, tk.END)
            self.teacher_entry.insert(0, record.get('teacher', ''))

            self.customer_var.set(record.get('customer', ''))
            self.type_combobox.set(record.get('type', ''))
            self.payment_combobox.set(record.get('payment', ''))
            self.status_combobox.set(record.get('status', ''))

            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, record.get('amount', ''))

            self._on_payment_method_selected()
            # ▲▲▲▲▲ 修改结束 ▲▲▲▲▲

            self.save_appointment_button.config(text="更新预约")

    def _clear_appointment_fields(self):
        """(V5 - 修复下拉列表锁定问题)"""
        self.editing_id = None
        now = datetime.now()

        # 1. 重置日期
        self.year_combo.set(str(now.year))
        self.month_combo.set(f"{now.month:02d}")
        self.day_combo.set(f"{now.day:02d}")
        self.hour_combo.set(f"{now.hour:02d}")
        self.minute_combo.set("00")

        # 2. 清空输入
        self.teacher_entry.delete(0, tk.END)
        self.customer_var.set('')
        self.amount_entry.delete(0, tk.END)
        self.payment_combobox.set('')
        self.status_combobox.set('是')

        # 3. ▼▼▼ 强制还原全量列表，解决"卡死"问题 ▼▼▼
        if hasattr(self, 'all_appt_types'):
            self.type_combobox['values'] = self.all_appt_types
        else:
            self.type_combobox['values'] = ["中医", "理疗", "办卡充值", "中药", "合作收入", "茶包", "足浴包", "大膏药",
                                            "解酒饮", "膏药"]
        self.type_combobox.set('')

        # 4. ▼▼▼ 强制解锁医师输入框 ▼▼▼
        self.teacher_entry.config(state='normal')

        # 5. 重置渠道
        self.channel_combobox.config(state='normal')
        self.channel_combobox.set('')
        self.channel_combobox.config(state='disabled')

        self.save_appointment_button.config(text="保存")
        if self.appointment_tree.selection():
            self.appointment_tree.selection_remove(self.appointment_tree.selection())

        self.teacher_entry.focus_set()

    def _delete_appointment(self):
        # 1. 获取在表格中选中的所有行的 ID
        selected_iids = self.appointment_tree.selection()
        if not selected_iids:
            messagebox.showwarning("操作无效", "请先在列表中选择要删除的记录。")
            return

        # 2. 弹窗二次确认
        if messagebox.askokcancel("确认删除",
                                  f"确定要永久删除选中的 {len(selected_iids)} 条记录吗？\n\n注意：此操作无法撤销。"):

            # 将选中的 ID 转为集合(set)，提高匹配速度
            ids_to_delete = set(selected_iids)
            actual_deleted_count = 0

            # 3. 核心修复：遍历所有用户的数据，无视归属，全局匹配并删除
            # all_data['user_data'] 包含了包括 admin、普通员工在内的所有人
            for username, user_data_content in self.all_data.get('user_data', {}).items():
                if 'appointments' in user_data_content:
                    # 记录删除前的数量
                    original_length = len(user_data_content['appointments'])

                    # 过滤掉所有 ID 在 ids_to_delete 中的记录
                    user_data_content['appointments'][:] = [
                        p for p in user_data_content['appointments'] if p['id'] not in ids_to_delete
                    ]

                    # 累加真正被删除的条数
                    actual_deleted_count += (original_length - len(user_data_content['appointments']))

            # 4. 如果确实删除了数据，则保存并刷新界面
            if actual_deleted_count > 0:
                self._save_database()
                # _populate_appointment_treeview 内部会自动调用 _rebuild_view_lists 重新合并数据
                self._populate_appointment_treeview()
                messagebox.showinfo("成功", f"已彻底删除 {actual_deleted_count} 条记录。")
            else:
                # 兜底：如果没找到对应记录
                messagebox.showwarning("提示", "未找到匹配的记录，可能已被其他操作删除或数据不同步。")
    def _on_payment_method_selected(self, event=None):
        """
        (V2 - 美团/小红书适配版)
        美团、小红书 -> 现金。
        """
        selected_payment = self.payment_combobox.get().strip()

        target_channel = ""

        # ▼▼▼ 核心修改：现金类增加 美团、小红书 ▼▼▼
        if selected_payment in ["现金", "美团", "大众点评", "合作诊所-现金", "小红书"]:
            target_channel = "现金"
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        elif selected_payment in ["银行", "收钱吧", "微医"]:
            target_channel = "银行"
        else:
            target_channel = "无"

        self.channel_combobox.config(state='normal')
        self.channel_combobox.set(target_channel)
        self.channel_combobox.config(state='disabled')
    def _on_type_selected(self, event=None):
        """
        (V19 - 中药关联未指定版)
        逻辑更新：
        1. 选中 [中药] 或 [合作收入] -> 医师自动填 [未指定] 并锁定。
        2. 选中 [大膏药] -> 医师自动填 [李福兴]。
        """
        selected_type = self.type_combobox.get()

        # ▼▼▼ 核心修改：中药 -> 自动填“未指定” ▼▼▼
        if selected_type in ["中药", "合作收入"]:
            self.teacher_entry.config(state='normal')  # 先解锁才能写入
            self.teacher_entry.delete(0, tk.END)
            self.teacher_entry.insert(0, "未指定")  # 填入特定名称
            self.teacher_entry.config(state='disabled')  # 填完锁定

        elif selected_type == "大膏药":
            self.teacher_entry.config(state='normal')
            self.teacher_entry.delete(0, tk.END)
            self.teacher_entry.insert(0, "李福兴")
            # 李福兴这里通常不需要锁定，或者根据您习惯保持可编辑

        else:
            # 其他类型（中医、理疗、茶包等）保持正常可输入状态
            self.teacher_entry.config(state='normal')

    def export_for_lemon_cloud(self):
        self._rebuild_view_lists()
        current_iids = self.appointment_tree.get_children()
        appointments_in_view = [a for a in self.view_appointments if a['id'] in current_iids]

        if not appointments_in_view:
            messagebox.showinfo("提示", "无记录可导出。")
            return

        display_fields = {
            'date': {'label': '日期'},
            'customer': {'label': '客户'},
            'type': {'label': '类型'},
            'teacher': {'label': '医师'},
            'channel': {'label': '渠道'},
            'amount': {'label': '金额'}
        }

        dialog = AdvancedFilterDialog(self.root, "导出至柠檬云", appointments_in_view, display_fields)
        dialog.add_custom_selection_button("全选 [银行]", lambda x: x.get('channel') == '银行')
        dialog.add_custom_selection_button("全选 [现金]", lambda x: x.get('channel') == '现金')
        dialog.add_custom_selection_button("全选 [有效渠道]", lambda x: x.get('channel') != '无')
        dialog.add_custom_selection_button("全部勾选", lambda x: True)
        dialog.add_custom_selection_button("全部取消", lambda x: False)

        result = dialog.show()
        if not result or not result.get('selected_ids'): return

        selected_ids = result['selected_ids']
        target_appointments = [a for a in appointments_in_view if a.get('id') in selected_ids]

        bank_records = [r for r in target_appointments if r.get('channel') in ["银行", "收钱吧", "微医"]]
        cash_records = [r for r in target_appointments if r.get('channel') in ["现金", "美团", "大众点评", "小红书"]]

        def transform_appointment(record):
            r_type = record.get("type", "").strip()
            r_teacher = record.get("teacher", "未知").strip()

            # ▼▼▼ 核心：膏药也隐藏名字 ▼▼▼
            if r_type in ["茶包", "足浴包", "中药", "合作收入", "膏药"]:
                formatted_category = r_type
            else:
                formatted_category = f"{r_type}-{r_teacher}"

            return {
                "date": record.get("date"),
                "customer": record.get("customer"),
                "type": r_type,
                "teacher": formatted_category,
                "amount": record.get("amount"),
                "payment": record.get("payment")
            }

        final_cash = [transform_appointment(r) for r in cash_records]
        final_bank = [transform_appointment(r) for r in bank_records]

        summary_msgs = []
        if final_cash:
            c, e = self._process_lemon_template(final_cash, '现金日记账导入模板.xls')
            if e:
                messagebox.showerror("现金导出错误", e)
            else:
                summary_msgs.append(f"现金: {c}条")

        if final_bank:
            c, e = self._process_lemon_template(final_bank, '银行日记账导入模板.xls')
            if e:
                messagebox.showerror("银行导出错误", e)
            else:
                summary_msgs.append(f"银行: {c}条")

        if summary_msgs: messagebox.showinfo("导出完成", " ".join(summary_msgs))
    def _rebuild_view_lists(self):
        """
        (新增) 动态重新构建当前用户的数据视图。
        确保在显示数据前，总能反映最新的全局共享设置和数据变更。
        """
        # 1. 先重置视图，只包含用户自己的最新数据
        # self.current_..._appointments 是在 __init__ 中定义的原始数据源
        self.view_prescriptions = list(self.current_user_prescriptions)
        self.view_appointments = list(self.current_user_appointments)

        # 2. 检查全局共享开关的最新状态
        is_global_sharing_enabled = self.all_data.get('config_data', {}).get('enable_global_data_sharing', False)

        # 3. 如果不是管理员，但共享已开启，则追加 admin 的数据
        if not self.is_admin and is_global_sharing_enabled:
            admin_data = self.all_data['user_data'].get('admin', {})
            self.view_prescriptions.extend(admin_data.get('prescriptions', []))
            self.view_appointments.extend(admin_data.get('appointments', []))

        # 4. 如果是管理员，则追加所有其他用户的数据
        elif self.is_admin:
            for user, user_data_content in self.all_data.get('user_data', {}).items():
                if user != 'admin':
                    self.view_prescriptions.extend(user_data_content.get('prescriptions', []))
                    self.view_appointments.extend(user_data_content.get('appointments', []))

    def _load_database(self):
        pass

    def _save_database(self):
        """(V15 - 最终修正版) 保存整个 all_data 字典到文件，并使用硬编码的密钥加密。"""
        try:
            # 1. 实例化加密器
            f = Fernet(SECRET_KEY_CONSTANT)
            db_file = 'clinic_data.db'

            # 2. 序列化和压缩数据
            pickled_data = pickle.dumps(self.all_data, pickle.HIGHEST_PROTOCOL)
            compressed_data = lzma.compress(pickled_data)

            # 3. 【关键步骤】在写入前，对压缩后的数据进行加密
            encrypted_data = f.encrypt(compressed_data)

            # 4. 将最终的加密数据写入文件
            with open(db_file, 'wb') as file:
                file.write(encrypted_data)

        except Exception as e:
            # 使用 self.root 来确保弹窗在主窗口之上
            if hasattr(self, 'root') and self.root:
                messagebox.showerror("数据库保存错误", f"无法加密并保存数据库文件: {str(e)}", parent=self.root)
            else:
                # 在某些情况下（如预加载时），可能还没有 self.root
                print(f"加密并保存数据库时出错: {e}")

    def _bind_common_events(self):
        """绑定通用的、与具体页面无关的快捷键"""
        # ▼▼▼ 更新这里的函数调用 ▼▼▼
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        # ▲▲▲ 更新结束 ▲▲▲

        self.root.bind("<Alt-F4>", lambda e: self._on_window_close())
        self.root.bind("<Control-q>", lambda e: self._on_window_close())

    def _bind_prescription_events(self):
        """只绑定药方管理页面相关的事件"""
        self.name_entry.bind("<KeyRelease>", self.search_medicine)
        self.name_entry.bind("<Down>", self.navigate_listbox)
        self.name_entry.bind("<Up>", self.navigate_listbox)
        self.name_entry.bind("<Return>", self.confirm_selection)
        self.search_results_listbox.bind("<<ListboxSelect>>", self._update_info_panel)
        self.search_results_listbox.bind("<Double-Button-1>", self.confirm_selection)
        self.grams_entry.bind("<Return>", self.focus_add_button)
        self.add_button.bind("<Return>", lambda e: self.add_or_update_prescription())
        self.tree.bind("<Delete>", self.delete_selected_item)
        self.tree.bind("<Double-Button-1>", self.load_item_for_edit)
        # 快捷键
        self.root.bind("<Control-f>", lambda e: self.open_find_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_current_prescription_to_db())
        self.root.bind("<Control-Return>", lambda e: self.add_or_update_prescription())
        self.root.bind("<Control-Delete>", lambda e: self.clear_all())
        self.root.bind("<Control-e>", lambda e: self.load_item_for_edit())
        self.root.bind("<Alt-n>", lambda e: self.name_entry.focus_set())
        self.root.bind("<Alt-g>", lambda e: self.grams_entry.focus_set())
        self.root.bind("<Escape>", self.handle_escape_key)

    def _bind_appointment_events(self):
        """只绑定信息登记页面相关的事件"""
        # (这里我们将 _bind_teacher_search_events 的内容移入)
        self.teacher_entry.bind("<KeyRelease>", self._search_teacher)
        self.teacher_entry.bind("<Down>", self._navigate_teacher_listbox)
        self.teacher_entry.bind("<Up>", self._navigate_teacher_listbox)
        self.teacher_entry.bind("<Return>", self._confirm_teacher_selection)
        self.teacher_entry.bind("<FocusOut>", self._hide_teacher_listbox)
        self.teacher_results_listbox.bind("<ButtonRelease-1>", self._confirm_teacher_selection)
        self.teacher_results_listbox.bind("<Double-Button-1>", self._confirm_teacher_selection)
        self.teacher_results_listbox.bind("<Return>", self._confirm_teacher_selection)

    def _on_window_close(self):
        """
        (V2 - 上下文感知版)
        智能处理窗口关闭事件。
        - 如果是主窗口，则安全退出整个程序。
        - 如果是管理员代管的子窗口，则只关闭自己，不影响主窗口。
        """
        try:
            # 无论哪个窗口关闭，都应该尝试保存整个数据库，因为可能有修改
            self._save_database()
        except Exception as e:
            if messagebox.askokcancel("关闭确认", f"保存数据时出现错误：{str(e)}\n\n是否仍要关闭此窗口？"):
                pass
            else:
                return  # 如果用户取消，则不执行任何关闭操作

        # ▼▼▼▼▼ 核心逻辑：根据窗口类型执行不同操作 ▼▼▼▼▼
        if self.is_admin_view:
            # 这是管理员代管的 Toplevel 子窗口。
            # 只需销毁这个窗口本身，不要调用 quit()，以免终止主循环。
            self.root.destroy()
        else:
            # 这是程序的主窗口 (Tk)。
            # 调用 quit() 来终止 mainloop，从而安全退出整个应用程序。
            self.root.quit()
        # ▲▲▲▲▲ 修改结束 ▲▲▲▲▲

    def _get_fuzzy_string(self, text):
        replacements = {'sh': 's', 'ch': 'c', 'zh': 'z', 'n': 'l', 'h': 'f', 'l': 'n'}
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def navigate_listbox(self, event):
        lb = self.search_results_listbox
        sel = lb.curselection()
        current = sel[0] if sel else -1
        if event.keysym == "Down":
            next_idx = min(current + 1, lb.size() - 1)
        else:
            next_idx = max(current - 1, 0)
        if next_idx >= 0:
            lb.selection_clear(0, tk.END)
            lb.selection_set(next_idx)
            lb.activate(next_idx)
            lb.see(next_idx)
        self._update_info_panel()
        return "break"

    def confirm_selection(self, event=None):
        sel = self.search_results_listbox.curselection()
        if not sel: return "break"

        medicine_name = self.search_results_listbox.get(sel[0])
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, medicine_name)
        self.search_results_listbox.delete(0, tk.END)
        self.grams_entry.focus_set()
        self._update_info_panel()

        # --- 智能单位：智能单位选择逻辑 ---
        medicine_data = self.all_data['config_data']['medicine_data']
        medicine_unit = medicine_data.get(medicine_name, {}).get('unit')

        if medicine_unit:
            if medicine_unit in ['袋', '盒', '瓶']:
                self.unit_combobox.set(medicine_unit)
                self.unit_combobox.config(state='readonly')
            else:
                self.unit_combobox.set('克')
                self.unit_combobox.config(state='normal')
        else:
            self.unit_combobox.set('克')
            self.unit_combobox.config(state='normal')

        return "break"
    def _update_info_panel(self, event=None):
        selection_indices = self.search_results_listbox.curselection()
        if not selection_indices:
            self.info_price_label.config(text="- -")
            return
        selected_name = self.search_results_listbox.get(selection_indices[0])
        medicine_info = self.all_data['config_data']['medicine_data'].get(selected_name, {})
        price = medicine_info.get('price')
        if price is not None:
            unit = medicine_info.get('unit', '克')
            self.info_price_label.config(text=f"{price:.4f} 元 / {unit}")
        else:
            self.info_price_label.config(text="未知")

    def delete_selected_item(self, event=None):
        if self.edit_mode_index is not None:
            messagebox.showwarning("提示", "请先完成或取消当前编辑操作，再删除药品。")
            return
        selected_iids = self.tree.selection()
        if not selected_iids:
            return
        names_to_delete = {self.tree.item(iid, 'values')[0] for iid in selected_iids}
        self.prescription = [p for p in self.prescription if p['name'] not in names_to_delete]
        self.update_prescription_display()
        self.name_entry.focus_set()

    def load_item_for_edit(self, event=None):
        if self.edit_mode_index is not None:
            messagebox.showwarning("提示", "您已处于编辑模式，请先完成当前修改。")
            return
        selected_iid = self.tree.focus()
        if not selected_iid:
            return
        item_name = self.tree.item(selected_iid, 'values')[0]
        for index, p_item in enumerate(self.prescription):
            if p_item['name'] == item_name:
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, p_item['name'])
                self.grams_entry.delete(0, tk.END)

                # 【核心修改】使用 get() 方法安全地读取原始数据，并提供兼容旧数据的后备方案
                display_quantity = p_item.get('display_quantity', p_item['grams'])
                display_unit = p_item.get('display_unit', '克 (g)')

                self.grams_entry.insert(0, str(display_quantity))
                self.unit_combobox.set(display_unit)

                # 附加修正：同时恢复单位下拉框的“只读”状态
                medicine_data = self.all_data['config_data']['medicine_data']
                medicine_info = medicine_data.get(p_item['name'], {})
                base_unit = medicine_info.get('unit', '克')
                if base_unit in ['袋', '盒', '瓶']:
                    self.unit_combobox.config(state='readonly')
                else:
                    self.unit_combobox.config(state='normal')

                self.enter_edit_mode(index)
                self.grams_entry.focus_set()  # 将焦点设置到剂量框，方便修改
                return
    def clear_all(self):
        if self.edit_mode_index is not None:
            messagebox.showwarning("提示", "请先完成或取消当前编辑操作。")
            return
        if messagebox.askokcancel("确认", "确定要清空当前所有药方吗？", default=messagebox.OK):
            self.prescription = []
            self.patient_name_var.set("")
            self.date_var.set(datetime.now().strftime('%Y-%m-%d'))
            self.doses_var.set('1')
            self.update_prescription_display()
            self.name_entry.focus_set()

    def save_current_prescription_to_db(self):
        if not self.prescription:
            messagebox.showwarning("提示", "当前药方为空，无需保存。")
            return
        new_record = {"id": datetime.now().isoformat(), "patient_name": self.patient_name_var.get(),
                      "date": self.date_var.get(), "doses": self.doses_var.get(), "prescription": self.prescription}
        self.current_user_prescriptions.append(new_record)
        self._save_database()
        messagebox.showinfo("成功", "当前药方已成功保存到历史记录。")

    def open_prescription_history_window(self):
        history_win = tk.Toplevel(self.root)
        history_win.title("历史药方记录")
        history_win.geometry("600x400")
        history_win.transient(self.root)
        history_win.grab_set()

        cols = ("date", "name", "doses")
        tree = ttk.Treeview(history_win, columns=cols, show='headings')
        tree.heading("date", text="日期")
        tree.heading("name", text="姓名")
        tree.heading("doses", text="剂数")
        tree.column("date", width=120, anchor='center')
        tree.column("name", width=150, anchor='center')
        tree.column("doses", width=50, anchor='center')

        sorted_prescriptions = sorted(self.current_user_prescriptions, key=lambda x: x.get('id'), reverse=True)
        for record in sorted_prescriptions:
            tree.insert("", "end", iid=record['id'], values=(
                record.get('date', ''), record.get('patient_name', ''), record.get('doses', '')))
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def load_selected():
            selected_iid = tree.focus()
            if not selected_iid:
                return
            if self.prescription and messagebox.askquestion("确认", "加载新药方会清空当前内容，确定要继续吗？",
                                                            parent=history_win) == 'no':
                return
            record_to_load = next((p for p in self.current_user_prescriptions if p['id'] == selected_iid), None)
            if record_to_load:
                self.patient_name_var.set(record_to_load.get("patient_name", ""))
                self.date_var.set(record_to_load.get("date", datetime.now().strftime('%Y-%m-%d')))
                self.doses_var.set(record_to_load.get("doses", "1"))
                self.prescription = record_to_load["prescription"]
                self.update_prescription_display()
                history_win.destroy()

        def delete_selected():
            selected_iids = tree.selection()
            if not selected_iids:
                return
            if messagebox.askokcancel("确认删除", f"确定要永久删除选中的 {len(selected_iids)} 条记录吗？",
                                      parent=history_win):
                # ▼▼▼▼▼ 核心Bug修复：从正确的 self.current_user_prescriptions 中删除 ▼▼▼▼▼
                self.current_user_prescriptions[:] = [p for p in self.current_user_prescriptions if
                                                      p['id'] not in selected_iids]
                # ▲▲▲▲▲ 修复结束 ▲▲▲▲▲
                self._save_database()
                history_win.destroy()
                # 重新打开窗口以刷新视图
                self.open_prescription_history_window()

    def add_or_update_prescription(self):
        name, quantity_str, selected_unit = self.name_entry.get().strip(), self.grams_entry.get().strip(), self.unit_combobox.get()
        medicine_data = self.all_data['config_data']['medicine_data']
        if not name:
            if self.edit_mode_index is None:
                return
            else:
                messagebox.showerror("错误", "药品名称不能为空！")
                return
        if name not in medicine_data:
            messagebox.showerror("错误", f"未找到名为 '{name}' 的中药。")
            return
        if not quantity_str:
            self.grams_entry.focus_set()
            return
        if not re.fullmatch(r'^[1-9]\d*(\.\d+)?$|^0\.\d+$', quantity_str):
            messagebox.showerror("输入错误", "剂量必须是大于0的数字！")
            self.grams_entry.delete(0, tk.END)
            self.grams_entry.focus_set()
            return

        grams = float(quantity_str) * self.units.get(selected_unit, 1)
        if grams < 0.001 and selected_unit != '毫克 (0.001g)':
            messagebox.showerror("输入错误", "最终计算的克数过小！")
            self.grams_entry.focus_set()
            return
        if selected_unit != '瓶' and selected_unit != '盒' and selected_unit != '袋':
            subtotal = (medicine_data[name]['price'] * grams) / 10
        else:
            subtotal = (medicine_data[name]['price'] * grams)

        # 【核心修改】创建一个包含所有需要信息的字典
        new_item_data = {
            "name": name,
            "grams": grams,  # 这是最终计算用于统计总量的克数/基本单位
            "subtotal": subtotal,
            "display_quantity": float(quantity_str),  # 保存用户输入的原始数量
            "display_unit": selected_unit  # 保存用户选择的原始单位
        }

        if self.edit_mode_index is not None:
            original_name = self.prescription[self.edit_mode_index]['name']
            if name != original_name and any(item['name'] == name for i, item in enumerate(self.prescription) if
                                             i != self.edit_mode_index):
                messagebox.showerror("错误", f"药方中已存在 '{name}'，无法将当前项修改为此药名。")
                return
            self.prescription[self.edit_mode_index] = new_item_data
            self.update_prescription_display()
            self.exit_edit_mode()
        else:
            if any(item['name'] == name for item in self.prescription):
                messagebox.showwarning("提示",
                                       f"药方中已经存在 '{name}'，请勿重复添加。\n\n如需修改剂量，请双击该项进行编辑。")
                return
            self.prescription.append(new_item_data)
            self.update_prescription_display()
            self.name_entry.delete(0, tk.END)
            self.grams_entry.delete(0, tk.END)
            self.populate_full_list()
            self.name_entry.focus_set()
    def enter_edit_mode(self, index):
        self.edit_mode_index = index
        self.add_button.config(text="更 新")
        self.clear_button.config(text="取消编辑", command=self.cancel_edit_mode)

    def exit_edit_mode(self):
        self.edit_mode_index = None
        self.add_button.config(text="添 加")
        self.clear_button.config(text="全部清空", command=self.clear_all)
        self.name_entry.delete(0, tk.END)
        self.grams_entry.delete(0, tk.END)
        self.unit_combobox.set('十克 (10g)')
        self.populate_full_list()
        self.name_entry.focus_set()

    def cancel_edit_mode(self):
        self.exit_edit_mode()

    def search_medicine(self, event):
        if event.keysym in ("Up", "Down", "Return", "Enter"):
            return
        search_term = self.name_entry.get().lower().strip()
        self.search_results_listbox.delete(0, tk.END)
        if not search_term:
            self.populate_full_list()
            return

        fuzzy_search_term = self._get_fuzzy_string(search_term)
        matches = []
        for name, pinyin_data in self.medicine_pinyin_map.items():
            priority = 0
            if name.lower().startswith(search_term):
                priority = 1
            elif pinyin_data['initials'].startswith(search_term):
                priority = 2
            elif search_term in pinyin_data['initials']:
                priority = 3
            elif any(s.startswith(search_term) for s in pinyin_data['syllable_initials']):
                priority = 4
            elif pinyin_data['full'].startswith(search_term):
                priority = 5
            elif pinyin_data['fuzzy_full'].startswith(fuzzy_search_term):
                priority = 6
            elif search_term in name.lower():
                priority = 7
            elif search_term in pinyin_data['full']:
                priority = 8
            elif fuzzy_search_term in pinyin_data['fuzzy_full']:
                priority = 9
            if priority > 0:
                matches.append((priority, name))

        matches.sort()
        seen = set()
        unique_names = []
        for _, name in matches:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        for name in unique_names:
            self.search_results_listbox.insert(tk.END, name)

    def open_calculator(self):
        calc_window = tk.Toplevel(self.root)
        calc_window.title("计算器")
        calc_window.geometry("320x420")
        calc_window.resizable(False, False)
        calc_window.transient(self.root)
        calc_window.grab_set()

        # 修复：使用master参数明确指定父窗口
        expression_var = tk.StringVar(master=calc_window)

        # 修复：为font.Font也指定root参数
        fonts = [font.Font(root=calc_window, family="Courier New", size=s) for s in [20, 16, 12, 10]]

        display_entry = ttk.Entry(calc_window, textvariable=expression_var, font=fonts[0], justify='left')
        display_entry.pack(fill='x', padx=10, pady=(15, 5), ipady=8)

        buttons_frame = ttk.Frame(calc_window, padding=(10, 0, 10, 10))
        buttons_frame.pack(fill='both', expand=True)
        buttons_data = [['C', '(', ')', '÷'], ['7', '8', '9', '×'], ['4', '5', '6', '-'],
                        ['1', '2', '3', '+'], ['del', '0', '.', '='], ['√', 'x²', 'xⁿ', 'Sci']]
        buttons_map = {'x²': '**2', 'xⁿ': '**', '√': '√('}

        def update_font_and_view(*args):
            display_entry.update_idletasks()
            w = display_entry.winfo_width()
            t = expression_var.get()
            if w < 10:
                return
            for f in fonts:
                if f.measure(t) < w - 15:
                    display_entry.config(font=f)
                    display_entry.xview_moveto(0)
                    return
            display_entry.config(font=fonts[-1])
            display_entry.xview_moveto(1.0)

        expression_var.trace_add("write", update_font_and_view)

        def insert_text_at_cursor(text):
            pos = display_entry.index(tk.INSERT)
            display_entry.insert(pos, text)
            display_entry.icursor(pos + len(text))

        def on_press(val):
            if val == 'C':
                expression_var.set('')
            elif val == 'del':
                pos = display_entry.index(tk.INSERT)
                if pos > 0:
                    t = expression_var.get()
                    expression_var.set(t[:pos - 1] + t[pos:])
                    display_entry.icursor(pos - 1)
            else:
                insert_text_at_cursor(buttons_map.get(val, val))

        def calculate():
            ctx = getcontext()
            ctx.prec = 50
            ctx.traps[Inexact] = False
            try:
                expr = expression_var.get().replace('×', '*').replace('÷', '/').replace('π',
                                                                                        str(Decimal(math.pi))).replace(
                    'e', str(Decimal(math.e)))
                if not expr:
                    return
                expr = re.sub(r'√\((.*?)\)', r'(\1).sqrt()', expr)
                expr = re.sub(r'(\d+\.?\d*)', r"Decimal('\1')", expr)
                expr = re.sub(r"Decimal\('(\d+)'\)\!", r'math.factorial(\1)', expr)
                safe_dict = {"Decimal": Decimal, "math": math, "sin": lambda x: Decimal(math.sin(float(x))),
                             "cos": lambda x: Decimal(math.cos(float(x))), "tan": lambda x: Decimal(math.tan(float(x))),
                             "log": lambda x: Decimal(math.log10(float(x))),
                             "ln": lambda x: Decimal(math.log(float(x))), "abs": abs}
                expression_var.set(eval(expr, {"__builtins__": None}, safe_dict).normalize().to_eng_string())
            except DivisionByZero:
                expression_var.set("除数不能为零")
            except Exception:
                expression_var.set("计算错误")

        def handle_key_press(event):
            if event.keysym in ('Left', 'Right', 'Home', 'End'):
                return
            if event.keysym == 'BackSpace':
                on_press('del')
            elif event.keysym in ('Return', 'KP_Enter'):
                calculate()
            elif event.char in "0123456789.+-()":
                insert_text_at_cursor(event.char)
            elif event.char == '*':
                insert_text_at_cursor('×')
            elif event.char == '/':
                insert_text_at_cursor('÷')
            elif event.char == '^':
                insert_text_at_cursor('**')
            return "break"

        display_entry.bind("<KeyPress>", handle_key_press)
        display_entry.focus_set()

        for r, row in enumerate(buttons_data):
            for c, val in enumerate(row):
                if val == '=':
                    cmd = calculate
                elif val == 'Sci':
                    def open_sci_win():
                        s_w = tk.Toplevel(calc_window)
                        s_w.title("Functions")
                        s_w.resizable(False, False)
                        s_w.transient(calc_window)
                        s_w.grab_set()
                        s_f = ttk.Frame(s_w, padding=10)
                        s_f.pack()
                        s_b = [['sin(', 'cos(', 'tan('], ['log(', 'ln(', 'abs('], ['π', 'e', '!']]
                        for r_s, row_s in enumerate(s_b):
                            for c_s, txt_s in enumerate(row_s):
                                ttk.Button(s_f, text=txt_s, command=lambda t=txt_s: (
                                    insert_text_at_cursor(t), s_w.destroy())).grid(row=r_s, column=c_s, padx=2, pady=2,
                                                                                   sticky='ew')

                    cmd = open_sci_win
                else:
                    cmd = lambda v=val: on_press(v)
                ttk.Button(buttons_frame, text=val, command=cmd).grid(row=r, column=c, sticky="nsew", padx=1, pady=1,
                                                                      ipady=5)
            buttons_frame.rowconfigure(r, weight=1)
            [buttons_frame.columnconfigure(i, weight=1) for i in range(len(row))]
        calc_window.after(100, update_font_and_view)
        calc_window.wait_window()

    def open_find_dialog(self):
        if not self.prescription:
            messagebox.showinfo("提示", "当前药方为空，无需查找。")
            return
        find_window = tk.Toplevel(self.root)
        find_window.title("查找药方中的项目")
        find_window.geometry("300x150")
        find_window.resizable(False, False)
        find_window.transient(self.root)
        find_window.grab_set()

        frame = ttk.Frame(find_window, padding=10)
        frame.pack(expand=True, fill="both")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="药名 (可留空):").grid(row=0, column=0, sticky="w", pady=2)
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="剂量(克) (可留空):").grid(row=1, column=0, sticky="w", pady=2)
        grams_entry = ttk.Entry(frame)
        grams_entry.grid(row=1, column=1, sticky="ew", pady=2)

        def perform_search():
            name_q, grams_q = name_entry.get().strip().lower(), grams_entry.get().strip()
            if not any([name_q, grams_q]):
                messagebox.showwarning("输入错误", "请输入至少一个查找条件！", parent=find_window)
                return
            found_iids = []
            for iid in self.tree.get_children():
                vals = self.tree.item(iid, 'values')
                try:
                    if (not name_q or name_q in vals[0].lower()) and (
                            not grams_q or float(grams_q) == float(vals[1])):
                        found_iids.append(iid)
                except ValueError:
                    messagebox.showerror("输入错误", "剂量必须是有效的数字！", parent=find_window)
                    return
            if found_iids:
                self.tree.selection_set(found_iids)
                self.tree.see(found_iids[0])
                find_window.destroy()
            else:
                messagebox.showinfo("未找到", "在当前药方中未找到匹配的药品。", parent=find_window)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="查 找", command=perform_search).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取 消", command=find_window.destroy).pack(side="left", padx=5)
        name_entry.focus_set()
        [entry.bind("<Return>", lambda e: perform_search()) for entry in [name_entry, grams_entry]]
        self.root.wait_window(find_window)

    def handle_escape_key(self, event=None):
        if self.search_results_listbox.size() > 0:
            self.search_results_listbox.delete(0, tk.END)
            self._update_info_panel()
        # 隐藏老师搜索列表框
        if self.teacher_results_listbox.winfo_viewable():
            self.teacher_results_listbox.grid_remove()
        if self.root.focus_get() != self.name_entry:
            self.name_entry.focus_set()
        elif self.edit_mode_index is not None:
            self.cancel_edit_mode()
        return "break"

    def focus_add_button(self, event=None):
        self.add_button.focus_set()
        return "break"

    def populate_full_list(self):
        self.search_results_listbox.delete(0, tk.END)
        # --- 修改点 ---
        medicine_names = sorted(self.all_data['config_data'].get('medicine_data', {}).keys())
        for name in medicine_names:
            self.search_results_listbox.insert(tk.END, name)


if __name__ == "__main__":
    # 启用DPI感知，使界面在高分屏上更清晰
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"DPI Awareness setting failed: {e}")

    # 使用循环来处理登录和注销，允许用户切换账号
    while True:
        # 1. 预加载加密的数据库文件
        all_data = _preload_user_data()
        login_accounts = {'users': all_data.get('user_accounts', {})}

        # 2. 运行登录窗口
        login_app = LoginWindow(login_accounts)
        login_result = login_app.run()

        # 3. 检查登录结果，如果成功则继续
        if login_result:
            # --- 【文件合并与更新逻辑】 ---

            # 1. 定义一个健壮的CSV读取函数，使其能自动处理 utf-8 和 gbk 编码
            def robust_read_csv(filepath, **kwargs):
                try:
                    # 优先尝试 utf-8，这是更标准的格式
                    return pd.read_csv(filepath, encoding='utf-8', **kwargs)
                except UnicodeDecodeError:
                    # 如果失败（通常意味着是Excel/WPS生成的中文CSV），则使用 gbk
                    return pd.read_csv(filepath, encoding='gbk', **kwargs)


            csv_path = '112.csv'
            xls_path = '112.xls'

            # 检查更新文件(112.xls)是否存在
            if os.path.exists(xls_path):
                try:
                    import pandas as pd

                    # 2. 读取 Excel 文件，优先使用 openpyxl (兼容新格式)，失败则回退到 xlrd (兼容旧格式)
                    try:
                        df_update = pd.read_excel(xls_path, header=None, engine='openpyxl', skiprows=2)
                    except Exception:
                        df_update = pd.read_excel(xls_path, header=None, engine='xlrd', skiprows=2)

                    # 3. 使用健壮的函数来读取原始CSV数据
                    if os.path.exists(csv_path):
                        csv_header = robust_read_csv(csv_path, header=None, nrows=1)
                        df_source = robust_read_csv(csv_path, header=None, skiprows=1)
                    else:
                        # 如果原始CSV不存在，则创建一个空的DataFrame
                        df_source = pd.DataFrame(columns=range(df_update.shape[1]))
                        csv_header = pd.DataFrame()

                    # 4. (核心合并逻辑 - 这部分保持不变)
                    # 创建用于匹配的唯一键 (药品名 + 规格)
                    df_update['_merge_key'] = df_update.iloc[:, 2].astype(str).str.strip() + "||" + df_update.iloc[:,
                                                                                                    3].fillna(
                        '').astype(str).str.strip()
                    df_source['_merge_key'] = df_source.iloc[:, 2].astype(str).str.strip() + "||" + df_source.iloc[:,
                                                                                                    3].fillna(
                        '').astype(str).str.strip()

                    source_key_to_index = pd.Series(df_source.index, index=df_source._merge_key).to_dict()
                    new_rows = []
                    update_count = 0

                    for index, row in df_update.iterrows():
                        key = row['_merge_key']
                        if pd.isna(key) or key == "nan||nan": continue

                        # 如果在源文件中找到匹配项，则更新价格和单位
                        if key in source_key_to_index:
                            source_index = source_key_to_index[key]
                            df_source.iloc[source_index, 4] = row.iloc[4]  # 更新单位
                            df_source.iloc[source_index, 5] = row.iloc[5]  # 更新价格
                            update_count += 1
                        else:
                            # 如果是新项目，则添加到新行列表
                            new_rows.append(row)

                    # 合并新行到源数据
                    if new_rows:
                        df_new = pd.DataFrame(new_rows)
                        df_source.drop(columns=['_merge_key'], inplace=True, errors='ignore')
                        df_new.drop(columns=['_merge_key'], inplace=True, errors='ignore')
                        df_source = pd.concat([df_source, df_new], ignore_index=True)
                    else:
                        df_source.drop(columns=['_merge_key'], inplace=True, errors='ignore')

                    # 5. 将最终合并后的数据写回CSV文件，统一使用 utf-8-sig 编码
                    # 'utf-8-sig' 是一种能被Excel正确识别的UTF-8格式，可避免中文乱码
                    if not csv_header.empty:
                        csv_header.to_csv(csv_path, index=False, header=False, encoding='utf-8-sig')
                        df_source.to_csv(csv_path, index=False, header=False, encoding='utf-8-sig', mode='a')
                    else:
                        df_source.to_csv(csv_path, index=False, header=False, encoding='utf-8-sig')

                    print(f"数据合并完成！共更新 {update_count} 条记录，新增 {len(new_rows)} 条记录。")

                except Exception as e:
                    # 只有在发生真正无法处理的严重错误时，才弹出提示
                    temp_error_root = tk.Tk()
                    temp_error_root.withdraw()
                    messagebox.showerror("文件合并错误", f"合并 '{xls_path}' 到 '{csv_path}' 时出错：\n{e}",
                                         parent=temp_error_root)
                    temp_error_root.destroy()

            # --- 【启动主程序】 ---
            root = tk.Tk()
            root.geometry("1100x700")
            root.minsize(950, 600)

            # 将登录信息和加载好的全部数据传递给主程序界面
            app = MedicineApp(
                root=root,
                file_path=csv_path,
                all_db_data=all_data,
                username=login_result.get('username'),
                permissions=login_result.get('permissions', {})
            )

            # 运行主窗口循环
            root.mainloop()

            # 检查主程序退出后，是否是用户请求“切换账号”
            if hasattr(app, 'logout_request') and app.logout_request:
                continue  # 如果是，则继续外层while循环，重新显示登录界面
            else:
                break  # 否则，退出循环，结束程序
        else:
            # 如果登录失败或用户关闭了登录窗口，则直接退出
            break