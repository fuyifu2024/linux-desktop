# 构建与更新

## 环境要求

在专用构建虚拟机使用 Ubuntu 26.04，至少 40GB 空闲磁盘、8GB 内存。
本项目开发所在 Pi 只有约 4GB 空闲磁盘，不能承担完整镜像构建。
构建工具：git、python3、dpkg-dev、xorriso、squashfs-tools、libguestfs-tools、qemu-utils。

## rootfs

仅在独立 chroot 中复制源码到 `/opt/linux-desktop`，创建私有 `/run/linux-desktop-image-build` 标记，再运行 `scripts/customize-rootfs.sh`。
不要在宿主系统创建这个标记。脚本会安装桌面组件并清理 machine-id。
软件包、GNOME 扩展、Firefox的实际来源和兼容性仍需在26.04构建环境核实；清单不是已锁定的发布依赖。

## ARM 磁盘镜像

从 Ubuntu 官方获取 26.04 Pi 镜像或 ARM64 UEFI cloud image；在下载端验证官方签名的 SHA256SUMS 后解压。
输入必须是可由 libguestfs 检查的非压缩镜像，并具有至少12GB文件系统空闲空间。只增加虚拟磁盘容量不会扩展分区和文件系统，须先用 virt-resize 制作副本并扩展根分区。

```sh
bash scripts/build-image.sh pi5 /path/base.img VERIFIED_SHA256 /path/desktop.qcow2
qemu-img convert -O raw /path/desktop.qcow2 /path/desktop.img
```

使用原生ARM64构建机。镜像保留上游分区、引导和首次启动账户流程；GNOME首次启动、账户强制改密与磁盘自动扩容必须真机验收后才可公开发布。
Hangover/FEX尚未打包与固定版本，ARM兼容测试目前会报告运行时缺失。

## PC ISO

在隔离、可销毁的x86_64构建机中，将源码提交后运行：

```sh
sudo bash scripts/build-iso.sh base.iso VERIFIED_SHA256 casper/filesystem.squashfs desktop.iso
```

**此工具仅支持单层squashfs。Ubuntu现代桌面媒体可能使用多层文件系统；检测到多层时构建会拒绝。多层合成、安装源元数据和安装目标内容集成尚未实现，不可据此宣称Ubuntu26.04安装ISO已经完成。**

## 签名APT

安装 apt-utils、GnuPG。在独立签名环境生成专用密钥；不要提交私钥。

```sh
APT_SIGNING_KEY=FULL_FINGERPRINT APT_OUTPUT=/tmp/new-apt-repository bash scripts/apt-repository.sh
```

部署输出目录到 Pages；用户校验项目公布的指纹后导入公钥，在 deb822 `.sources` 中使用实际Pages地址、`Suites: stable`、`Components: main`、`Signed-By: /etc/apt/keyrings/linux-desktop.asc`。
仓库部署、密钥轮换和上游安全更新集成未实机验证。默认保留Ubuntu软件源，不覆盖系统软件包。
