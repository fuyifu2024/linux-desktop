# linux-desktop — 开发预览

基于 Ubuntu 26.04 LTS 的 GNOME 桌面发行版项目，面向 Windows 用户。

**当前交付是源码和可构建的桌面集成软件包，不是已经完成硬件认证的操作系统。没有正式版镜像，Windows 兼容性均未认证。**

## 已实现

- Windows 应用图形化管理器：独立 Wine 环境、EXE/MSI 安装、选择已安装程序、菜单快捷方式、运行、卸载和日志导出。
- 七语言离线教程及系统语言选择，GNOME 桌面默认配置和 Debian 软件包构建。
- Ubuntu 26.04 隔离 rootfs 定制、原始镜像校验、libguestfs 磁盘镜像定制、单层 ISO 重打包。
- 双架构源码与软件包 CI、签名 APT 仓库生成、要求真实验收证据的发布检查。

## 本地验证与构建

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build-deb.py
dpkg-deb --info build/linux-desktop_0.1.0~dev1_all.deb
```

只在测试虚拟机里安装：`sudo apt install ./build/linux-desktop*all.deb`。
软件包不会安装操作系统，也不会自动改变当前桌面会话。菜单提供 Windows Applications 和 Getting Started。
管理员可在 `/etc/linux-desktop/runtimes.json` 配置实际运行时绝对路径。
独立 Wine 环境不提供安全沙箱；日志可能含应用数据，分享前检查。

## 镜像与发布

见 [构建说明](docs/BUILD.md)、[验收与当前缺口](docs/ACCEPTANCE.md)。

首版硬件范围：选定的 Intel/AMD UEFI PC、Pi 5、ARM64 UEFI 虚拟机。
首批 Windows 验收应用：7-Zip、Notepad++、SumatraPDF、PuTTY。Office、Adobe、AutoCAD不作首版发布门槛。

自研代码 MIT；教程 CC BY 4.0；Ubuntu、Wine及所有上游组件遵守各自许可证。
项目采用独立工作名称，没有 Ubuntu 官方认证或背书。未收集遥测。
