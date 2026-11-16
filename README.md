# Keyguard noneRelease · HyperOS unlock-first（实验补丁）

这是一个 **Keyguard 原始 `noneRelease` 变体** 的自用 GitHub Actions 构建模板。目标是修复部分 Xiaomi / Redmi / POCO 系统在密码库锁定时，不显示只有 `AuthenticationAction` 的 Passkey 提示的问题。没有改动 Premium 权限判断，也没有启用 Google Play Credential Exchange 后端。

## 行为

1. 当 Keyguard **锁定**，且系统发起 **Passkey 获取请求**，且设备为 Xiaomi/Redmi/POCO 时，在 Credential Manager 返回一个不可自动选择的“解锁 Keyguard”虚拟 Passkey 入口。
2. 用户点此入口，进入 Keyguard 现有的解锁/验证 UI。
3. 解锁后按原始请求的 WebAuthn RP ID、来源和 `allowCredentials` 过滤真实 Passkey，展示实际账号列表。
4. 用户选中一个真实 Passkey，继续使用官方 `PasskeyProviderGetFlow`、`PasskeyProviderGetRequest` 和 WebAuthn authenticator 生成断言，并把 `GetCredentialResponse` 交回 Android。

假入口不含真实账号、凭据 ID 或私钥，不会自动完成登录。非小米设备及未锁库状态保持原流程。

## 工作流安装

将以下两个文件复制到 **你自己的 GitHub 仓库**。推荐使用私有仓库，以免构建日志和 APK 工件被公开；如果放在现有的 BitwardenPatch 仓库，工作流与原 Android/Browser 构建也互不干扰：

```text
.github/workflows/build-keyguard-none-release.yml
patches/keyguard/apply_unlock_first.py
```

进入仓库的 **Actions → Build Keyguard noneRelease (HyperOS unlock-first) → Run workflow**。默认检出上游 `r20261114`（Keyguard 3.8.1），自动应用补丁并运行 `:androidApp:assembleNoneRelease`。完成后在本次运行下的 **Artifacts** 里下载 APK。

### 签名 Secrets

工作流沿用原 `BitwardenPatch` Android 工作流的三个 Secrets：

- `SIGN_KEYSTORE_BASE64`：签名 JKS 文件的 Base64 内容。
- `KEYSTORE_PASSWORD`：JKS keystore 密码。
- `KEY_PASSWORD`：别名 `key0` 对应的私钥密码。

在另一仓库运行时，要重新配置这些 Secrets（GitHub 不会在不同仓库间复制）。使用原 BitwardenPatch 的密钥并不改变 Keyguard 的包名，两个 APK 彼此不冲突。

### 安装方式

- `parallel`（默认）：包名为 `com.artemchep.keyguard.hyperos`。**与原 Keyguard 并存**，用于测试。需要在 Android 密码/Passkey 提供方设置里选中它，再登录你自己的密码库。
- `original`：包名为 `com.artemchep.keyguard`，适合原来就用同一签名安装自编译 Keyguard 的用户。**若现有官方安装使用另一把签名密钥，则无法覆盖安装**。

Google Services 文件由工作流为 `noneRelease` 生成无真实 API 密钥的占位配置；未接入 Google Play/CXF。实际联网、登录和密码库仍由 Keyguard 原有逻辑处理。

## 版本与适配

构建会严格核对源码锚点；上游更新后如果关键结构不同，脚本会直接停止，避免构建出“补丁实际没有生效”的 APK。默认基线 `r20261114`。

## 静态与真机验证状态

已按 `r20261114` 的三个源文件检查全部替换锚点；脚本语法及工作流 YAML 静态解析通过。**尚未在本环境成功执行完整 Gradle/Rust 编译，也未在 HyperOS 3 真机测试**。因此 APK 能否成功产出以及小米 Credential Manager 会否展示该入口，需以 GitHub Actions 和真机结果为准。

建议真机检查顺序：保留官方应用、安装 `parallel` 测试版本 → 添加测试库/账号 → 在 Android 设置里指定测试版为 Passkey 提供方 → 完全锁定测试版密码库 → 在 WebAuthn 测试网站触发登录 → 检查是否出现“解锁 Keyguard”入口 → 解锁后检查是否只显示同一 RP ID 的真实 Passkey → 实测正确返回登录与取消操作。

## 许可

Keyguard 上游源码发布在可供个人使用的受限条款下，根目录 `LICENSE` 为 `All Rights Reserved`。本仓库只包含你自己的构建工作流和对公开源码的变更脚本。请仅在许可允许的范围内自用；不要公开分发改编后的 Keyguard APK。

Keyguard upstream: https://github.com/AChep/keyguard-app