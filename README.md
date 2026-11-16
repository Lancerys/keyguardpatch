# Keyguard noneRelease · HyperOS / Passkey patches

在 `AChep/keyguard-app` 官方正式标签上构建 `noneRelease`，通过独立补丁脚本添加已经在设备上验证的三个功能。仓库**只维护补丁和 GitHub Actions**，不直接同步或提交上游的整份源码。

## 三项补丁

1. **HyperOS 锁库解锁入口**：小米系设备的 Android Credential Manager 在 Keyguard 锁库时显示一个不可自动选中的入口，点选后进入原生解锁流程。
2. **解锁后选择真正的 Passkey**：根据原始请求的 RP ID、来源和允许的凭据过滤，显示 Keyguard 原生列表，并调用上游 WebAuthn 认证器签名。
3. **创建 Passkey 时预填登录信息**：参考 Bitwarden Android 的行为，在「新建登录条目」中填入 RP 网站名称、WebAuthn 用户名和来源 URI。保存到已有登录条目时不修改原有名称、用户名或 URI。

所有变更由 `patches/keyguard/apply_unlock_first.py` 在 CI 构建时应用；关键源码锚点不匹配就停止构建，防止发布未打补丁的版本。

## 周更与 Release

唯一工作流：`.github/workflows/build-keyguard-none-release.yml`，名称为 **Keyguard patched noneRelease (weekly upstream release)**。

- 每周日 **12:00 UTC / 新加坡时间 20:00** 检查 `AChep/keyguard-app` 的最新正式 GitHub Release（如 `r20261114`）。
- 如果同一上游标签已经完成发布，就跳过重复构建；发布新标签则重新克隆官方代码、应用补丁并构建签名 APK。
- 修改补丁或工作流并推送至 `main`，会触发重新构建并更新相同上游版本对应的 Release。
- 也可以通过 **Actions → Keyguard patched noneRelease (weekly upstream release) → Run workflow** 手动指定 `upstream_tag`，或将 `force_build` 设为 `true` 强制重建。
- 使用上游正式标签构建；若某次上游重构导致补丁锚点或编译失效，流程会失败并保留先前已发布的版本，不会自行猜测修改源代码。

使用：`./gradlew --no-daemon --max-workers=2 :androidApp:assembleNoneRelease -Pkeyguard.nativeCargo.cargoOffline=true`。构建前自动配置 Java 21、对应 Android NDK、Rust 工具链、原生预取和非 Google Play 占位设置。

## 安装和签名

稳定 APK 的包名固定为 **`com.artemchep.keyguard.hyperos`**，与之前的测试成功版本相同，可与官方 Keyguard 并存。后续使用相同签名密钥、上游递增版本号的 APK 即可覆盖升级。不能直接覆盖官方应用的签名包。

仓库 Actions Secrets：

- `SIGN_KEYSTORE_BASE64`
- `KEYSTORE_PASSWORD`
- `KEY_PASSWORD`

证书别名 `key0`。请始终保留同一签名密钥，否则 Android 不能直接升级已安装应用。

成功构建的 APK 和 `SHA256SUMS.txt` 会上传到当次 **Actions → Artifacts**，保留 14 天。

### 发布可见性与授权

**Keyguard 上游 `LICENSE` 标明 `All Rights Reserved`。** 当前仓库公开，因此自动 GitHub Release 仅发布版本说明，不上传改编的 APK。完整 APK 仍通过 Actions 构建产物提供用于个人验证。

如果未来将本仓库改为 **Private**，工作流可以将构建产物上传到仅仓库授权用户可访问的 GitHub Release。切换后手动启用一次 `force_build` 即可为当前上游版本补齐 Release 附件。

## 项目结构

```text
.github/workflows/build-keyguard-none-release.yml   # 唯一周更/正式构建工作流
patches/keyguard/apply_unlock_first.py               # 三项功能的锚点校验与源码补丁
README.md
```

上游地址：[AChep/keyguard-app](https://github.com/AChep/keyguard-app)。
