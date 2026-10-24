# S7 Pro Comic Reader (网易有道词典笔 S7 Pro 原生漫画阅读器)

专为网易有道词典笔 **S7 Pro (Y08_CV1813_V0 / 平头哥 CV1813H)** 定制的原生级 MiniApp 双列画卷漫画阅读器。

针对 1020×240 超长比例带鱼屏、Buildroot Linux 5.10 系统与低内存环境进行极致深度优化，支持 MTP 即插即读、474px 硬件点对点直通渲染、自适应横竖画幅瀑布流与视口虚拟滚动。

---

## 🌟 核心特性与架构设计

### 1. 474px 物理点对点直通渲染（彻底杜绝摩尔纹）
* **痛点根治**：词典笔屏幕横向 PPI 相对较低，若渲染引擎使用任意比例的双线性滤波（Bilinear Filtering）缩放高分辨率漫画，会引发严重的“网点摩尔纹（Moiré Pattern）”与文字发虚。
* **物理直通**：针对双列并排与单页 3/4 浏览，精准锁定 474px 物理像素基准；设置 `resizable: 'false'` 与 `resize: 'contain'`，绕过底层 `doLoadBitmap` 强行拉伸，实现 100% 锐利的网点画质与秒开体验。

### 2. 双列画卷瀑布流与自适应跨页单栏
* **横竖智能判定引擎**：基于图像真实宽高比 $\text{ratio} = \frac{W}{H}$ 毫秒级识别：
  * **竖向/方漫 ($\text{ratio} \le 1.05$)**：双列无缝拼接拼合，高度自适应对其，沉浸式翻阅。
  * **横向跨页大图 ($\text{ratio} > 1.05$)**：自适应切换为全宽单栏跨页长图，无需手动翻转。
* **双模式无缝折叠**：单击图片无缝进入 3/4 单页放大模式，再次单击无损返回瀑布流历史位置。

### 3. O(log N) 视口虚拟滚动与内存防爆机制
* 针对 120+ 页以上的高清长篇漫画，传统 DOM 渲染会迅速耗尽底层仅 4MB 的 `BitmapCache` 导致显存崩溃。
* 本阅读器采用 **二分查找视口滑动窗口（Viewport Windowing）**：仅在当前可视屏幕及前后少量缓冲区挂载真实 `<image>`，窗口外渲染几何恒定占位，实现百页超长漫画滚动 60FPS 丝滑不卡顿。

### 4. 480ms / 95px 触控消解状态机
* 针对电容触控屏的微抖动，自研手势冲突消解机：
  * **单双击严格消解**：250~480ms 延时窗口，精准区分单击（退出模式/返回位置）与双击（1.0x / 2.0x 局部细节放大）。
  * **全向边界约束**：单页模式下拖拽滑动严格对齐四周边沿，绝无越界留白黑边。
  * **左边缘向右侧滑**：符合人体工学系统级返回手势，逐级回退（单页放大 $\to$ 瀑布流 $\to$ 书架 $\to$ 系统桌面）。

### 5. 端侧双重转码进度条与 MTP 沙箱即插即读
* 完美对接出厂固件唯一暴露的三大 USB MTP 目录：`/userdisk/Favorite`、`/userdisk/Music` 与 `/userdisk/skip_re`。
* 内置轻量目录指纹对比，未修改时 **0ms 秒开**；新增漫画时端侧守护进程透明显示 **WebP 解码进度** 与 **474px 硬件缩略图生成进度**。

---

## 📂 漫画目录与导入规范

直接通过 Type-C 数据线连接电脑，在电脑文件管理器中打开词典笔存储的 **`Favorite`** 目录：

```text
/userdisk/Favorite/
├── 进击的巨人/
│   ├── 001.png          <- 第一张图片将自动作为书架封面
│   ├── 002.png
│   ├── 003.jpg
│   └── 004.webp         <- 支持 PNG, JPG, JPEG, WEBP
└── 猫咪日记/
    ├── 1.png
    ├── 2.png
    └── 10.png           <- 智能自然数值排序，绝不会出现 10 排在 2 前面
```

---

## 🛠️ 构建与部署指南

### 前置要求
* macOS / Linux 环境
* Python 3.8+
* 已提权并开启 SSH / ADB 调试连接的词典笔（默认 IP `192.168.2.2`）

### 1. 一键编译打包与直推部署
在仓库根目录下执行：

```bash
# 仅编译生成 AMR 字节码安装包 (生成 8001888800000001.amr)
python3 tools/build_amr.py src

# 编译并直推部署到设备、立即启动运行
python3 tools/build_amr.py src --deploy --start

# 指定自定义设备 IP 进行远程部署
python3 tools/build_amr.py src --device 192.168.31.200 --deploy --start
```

---

## 🏗️ 目录结构

```text
s7pro-comic-reader/
├── src/
│   ├── app.js               # 原生 MiniApp 全局生命周期与后退拦截
│   ├── index.js             # 核心业务组件 (书架、瀑布流、单页放大、触控状态机)
│   ├── manifest.json        # MiniApp 应用清单与权限声明
│   └── app_icon.png         # 桌面高清图标
├── tools/
│   ├── build_amr.py         # AMR 打包、证书签名与 QuickJS 字节码编译工具
│   ├── generate_comic_datasets.py # 生产级测试漫画数据集生成器
│   ├── run_full_manga_tests.py    # 自动化触控注入与全量测试套件
│   └── qjsc                 # 适用当前宿主机的 QuickJS 字节码编译器
└── README.md
```

---

## 📄 License

MIT License. Designed with excellence for hardware hacking and portable comic lovers.
