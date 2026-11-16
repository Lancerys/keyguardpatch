#!/usr/bin/env python3
"""Apply an anchor-checked HyperOS unlock-first patch to Keyguard r20261114.

The patch is intentionally source-only. A missing anchor aborts the build instead of
silently producing a stock APK. No real credential IDs or passwords are cached.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path('common/src/androidMain/kotlin/com/artemchep/keyguard/android')
SENTINEL = 'keyguard-hyperos-unlock-first-v1'


def replace_one(source: str, old: str, new: str, desc: str) -> str:
    hits = source.count(old)
    if hits != 1:
        raise RuntimeError(f'{desc}: expected exactly one anchor, got {hits}')
    return source.replace(old, new, 1)


def modify_handler(source: str) -> str:
    source = replace_one(
        source,
        'import androidx.credentials.provider.BeginGetCredentialResponse\n',
        'import androidx.credentials.provider.BeginGetCredentialResponse\n'
        'import androidx.credentials.provider.BeginGetPublicKeyCredentialOption\n'
        'import androidx.credentials.provider.PublicKeyCredentialEntry\n',
        'handler imports',
    )
    source = replace_one(
        source,
        '                createUnlockResponse(title)\n',
        '                createUnlockResponse(title, request)\n',
        'locked-vault handler',
    )
    source = replace_one(
        source,
        '''    private fun createUnlockResponse(
        title: String,
    ): BeginGetCredentialResponse {
        val pendingIntent = createGetUnlockCredentialPendingIntent()
''',
        '''    private fun createUnlockResponse(
        title: String,
        request: BeginGetCredentialRequest? = null,
    ): BeginGetCredentialResponse {
        // Xiaomi/HyperOS may hide AuthenticationAction-only provider responses.
        // This entry is NOT an actual credential and must never auto-select.
        // We do not read or cache secrets before the user unlocks the vault.
        if (request != null && isXiaomiDevice()) {
            val options = request.beginGetCredentialOptions
                .filterIsInstance<BeginGetPublicKeyCredentialOption>()
            if (options.isNotEmpty()) {
                val pendingIntent = createHyperOsUnlockFirstPendingIntent(title)
                return BeginGetCredentialResponse(
                    credentialEntries = options.map { option ->
                        PublicKeyCredentialEntry.Builder(
                            context = context,
                            username = title,
                            pendingIntent = pendingIntent,
                            beginGetPublicKeyCredentialOption = option,
                        )
                            .setDisplayName("Keyguard")
                            .setAutoSelectAllowed(false)
                            .build()
                    },
                )
            }
        }
        val pendingIntent = createGetUnlockCredentialPendingIntent()
''',
        'fake credential branch',
    )
    source = replace_one(
        source,
        '''    private fun createGetUnlockCredentialPendingIntent(): PendingIntent {
''',
        '''    private fun isXiaomiDevice(): Boolean =
        android.os.Build.MANUFACTURER.equals("Xiaomi", ignoreCase = true) ||
            android.os.Build.BRAND.equals("Redmi", ignoreCase = true) ||
            android.os.Build.BRAND.equals("POCO", ignoreCase = true)

    private fun createHyperOsUnlockFirstPendingIntent(title: String): PendingIntent {
        val args = PasskeyProviderGetActivityArgs(
            accountId = "",
            cipherId = PasskeyGetActivity.HYPEROS_UNLOCK_FIRST_SENTINEL,
            credId = "",
            cipherName = "Keyguard",
            credRpId = "",
            credUserDisplayName = title,
            requiresUserVerification = true,
            userVerified = false,
        )
        val intent = Intent(context, credentialProviderPlatformConfig.getPasskeyActivityClass)
            .putExtra(PasskeyGetActivity.KEY_ARGUMENTS, args)
        return createCredentialProviderPendingIntent(context, intent)
    }

    private fun createGetUnlockCredentialPendingIntent(): PendingIntent {
''',
        'fake credential pendingIntent',
    )
    return source


def modify_get(source: str) -> str:
    source = replace_one(source,
        'import androidx.compose.foundation.layout.*\n',
        'import androidx.compose.foundation.layout.*\n'
        'import androidx.compose.foundation.rememberScrollState\n'
        'import androidx.compose.foundation.verticalScroll\n',
        'passkey get compose imports')
    source = replace_one(source,
        'import androidx.credentials.GetCredentialResponse\n',
        'import androidx.credentials.GetCredentialResponse\n'
        'import androidx.credentials.GetPublicKeyCredentialOption\n',
        'credential request import')
    source = replace_one(source,
        'import com.artemchep.keyguard.common.model.MasterSession\n',
        'import com.artemchep.keyguard.common.model.MasterSession\n'
        'import com.artemchep.keyguard.common.model.DSecret\n'
        'import com.artemchep.keyguard.common.service.passkey.availablePasskeys\n'
        'import com.artemchep.keyguard.common.usecase.GetProfiles\n'
        'import com.artemchep.keyguard.common.usecase.PasskeyTarget\n'
        'import com.artemchep.keyguard.common.usecase.PasskeyTargetCheck\n'
        'import com.artemchep.keyguard.common.usecase.filterHiddenProfiles\n',
        'passkey model imports')
    source = replace_one(source,
        'import com.artemchep.keyguard.di.KeyguardKoinOwner\n',
        'import com.artemchep.keyguard.di.KeyguardKoinOwner\n'
        'import com.artemchep.keyguard.di.resolveOrCancel\n'
        'import com.artemchep.keyguard.common.io.bind\n'
        'import com.artemchep.keyguard.common.io.attempt\n',
        'passkey deps imports')
    source = replace_one(source,
        'import kotlinx.parcelize.Parcelize\n',
        'import kotlinx.parcelize.Parcelize\n'
        'import kotlinx.serialization.json.Json\n'
        'import com.artemchep.keyguard.util.webauthn.entity.GetPasskey\n',
        'JSON import')
    source = replace_one(source,
        '''    companion object {
        const val KEY_ARGUMENTS = "arguments"
    }
''',
        '''    companion object {
        const val KEY_ARGUMENTS = "arguments"
        const val HYPEROS_UNLOCK_FIRST_SENTINEL = "keyguard-hyperos-unlock-first-v1"
    }
''',
        'passkey sentinel')
    source = replace_one(source,
        '    protected val args: PasskeyProviderGetActivityArgs get() = requireNotNull(_args)\n',
        '''    protected val args: PasskeyProviderGetActivityArgs get() = requireNotNull(_args)
    private val isHyperOsUnlockFirst: Boolean
        get() = args.cipherId == HYPEROS_UNLOCK_FIRST_SENTINEL
''',
        'passkey sentinel check')
    source = replace_one(source,
        '''        class Error(
            val data: UiStateError,
        ) : UiState
''',
        '''        class Error(
            val data: UiStateError,
        ) : UiState

        class PickPasskey(
            val choices: List<HyperOsPasskeyChoice>,
            val onSelected: (PasskeyProviderGetActivityArgs) -> Unit,
        ) : UiState
''',
        'picker state')
    source = replace_one(source,
        '''    @SuppressLint("RestrictedApi")
    override fun onCreate(savedInstanceState: Bundle?) {
''',
        '''    private data class HyperOsPasskeyChoice(
        val title: String,
        val subtitle: String,
        val args: PasskeyProviderGetActivityArgs,
    )

    @SuppressLint("RestrictedApi")
    override fun onCreate(savedInstanceState: Bundle?) {
''',
        'picker model')
    source = replace_one(source,
        '''    private suspend fun handleCredentialRequest(
        session: MasterSession.Key,
        onRetry: () -> Unit,
    ) {
        val response = runCatching {
''',
        '''    private suspend fun handleCredentialRequest(
        session: MasterSession.Key,
        onRetry: () -> Unit,
    ) {
        if (isHyperOsUnlockFirst) {
            handleHyperOsUnlockFirst(session, onRetry)
            return
        }
        val response = runCatching {
''',
        'generic get dispatch')
    source = replace_one(source,
        '''    private suspend fun getCredentialErrorUiState(
''',
        '''    // This is a REAL get-credential PendingIntent. Unlike an AuthenticationAction,
    // it must finish with GetCredentialResponse after the user chooses a real passkey.
    private suspend fun handleHyperOsUnlockFirst(
        session: MasterSession.Key,
        onRetry: () -> Unit,
    ) {
        val choices = runCatching {
            withContext(Dispatchers.Default) { loadHyperOsChoices(session) }
        }.getOrElse { e ->
            recordException(e)
            uiStateSink.value = getCredentialErrorUiState(session, e, onRetry)
            return
        }
        if (choices.isEmpty()) {
            uiStateSink.value = getCredentialErrorUiState(
                session = session,
                exception = GetCredentialUnknownException("No matching passkeys in Keyguard"),
                onRetry = onRetry,
            )
            return
        }
        uiStateSink.value = UiState.PickPasskey(choices, onSelected@{ selectedArgs ->
            // Prevent double tap / multiple assertions.
            if (uiStateSink.value !is UiState.PickPasskey) return@onSelected
            uiStateSink.value = UiState.Loading
            lifecycleScope.launch {
                val response = runCatching {
                    withContext(Dispatchers.Default) {
                        passkeyProviderGetFlow.processUnlockedVault(
                            session = session,
                            request = getCredentialRequest,
                            args = selectedArgs,
                            userVerified = true,
                        )
                    }
                }.getOrElse { e ->
                    recordException(e)
                    uiStateSink.value = getCredentialErrorUiState(session, e, onRetry)
                    return@launch
                }
                withContext(Dispatchers.Default) {
                    passkeyProviderGetFlow.recordUsage(session, selectedArgs)
                }
                val resultIntent = Intent().apply {
                    PendingIntentHandler.setGetCredentialResponse(this, response)
                }
                setResult(RESULT_OK, resultIntent)
                finish()
            }
        })
    }

    private suspend fun loadHyperOsChoices(
        session: MasterSession.Key,
    ): List<HyperOsPasskeyChoice> {
        val option = getCredentialRequest.credentialOptions
            .filterIsInstance<GetPublicKeyCredentialOption>()
            .firstOrNull() ?: throw GetCredentialUnknownException("Not a passkey request")
        val json = koin.get<Json>()
        val requestOptions = json.decodeFromString<GetPasskey>(option.requestJson)
        val getCiphers = session.session.resolveOrCancel { get<GetCiphers>() }
        val getProfiles = session.session.resolveOrCancel { get<GetProfiles>() }
        val getPrivilegedApps = session.session.resolveOrCancel { get<GetPrivilegedApps>() }
        val privilegedApps = getPrivilegedApps().first()
        val passkeyUtils = koin.get<PasskeyUtils>()
        val callingAppInfo = getCredentialRequest.callingAppInfo
        val origin = passkeyUtils.callingAppOrigin(callingAppInfo, privilegedApps)
        val rpId = passkeyUtils.resolveAndValidateRpId(
            rpId = requestOptions.rpId,
            origin = origin,
            packageName = callingAppInfo.packageName,
        )
        val allowed = parseCredentialProviderBeginGetAllowedCredentialDescriptors(
            requestJson = option.requestJson,
            json = json,
        )
        val target = PasskeyTarget(rpId = rpId, allowed = allowed)
        val check = koin.get<PasskeyTargetCheck>()
        val ciphers = filterHiddenProfiles(
            getProfiles = getProfiles,
            getCiphers = getCiphers,
            filter = null,
        ).first()
        return ciphers.availablePasskeys().mapNotNull { (cipher, credential) ->
            val matches = check(credential, target).attempt().bind().isRight { it }
            if (!matches) return@mapNotNull null
            val displayName = sequenceOf(
                credential.userName,
                credential.userDisplayName,
                cipher.login?.username,
                cipher.name,
            ).filterNotNull().map(String::trim).firstOrNull { it.isNotEmpty() }
                ?: "Passkey"
            HyperOsPasskeyChoice(
                title = displayName,
                subtitle = cipher.name,
                args = PasskeyProviderGetActivityArgs(
                    accountId = cipher.accountId,
                    cipherId = cipher.id,
                    credId = credential.credentialId,
                    cipherName = cipher.name,
                    credRpId = credential.rpId,
                    credUserDisplayName = displayName,
                    requiresUserVerification = true,
                    userVerified = true,
                ),
            )
        }
    }

    private suspend fun getCredentialErrorUiState(
''',
        'passkey real selection flow')
    source = replace_one(source,
        '''                            is UiState.RequiresAuthentication -> {
''',
        '''                            is UiState.PickPasskey -> {
                                Column(
                                    modifier = androidx.compose.ui.Modifier
                                        .fillMaxSize()
                                        .verticalScroll(rememberScrollState())
                                        .padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(12.dp),
                                ) {
                                    Text("选择用于登录的 Passkey", style = MaterialTheme.typography.titleMedium)
                                    state.choices.forEach { choice ->
                                        OutlinedButton(
                                            onClick = { state.onSelected(choice.args) },
                                            modifier = androidx.compose.ui.Modifier.fillMaxWidth(),
                                        ) {
                                            Column {
                                                Text(choice.title)
                                                Text(choice.subtitle, style = MaterialTheme.typography.bodySmall)
                                            }
                                        }
                                    }
                                }
                            }

                            is UiState.RequiresAuthentication -> {
''',
        'passkey picker compose branch')
    return source


def modify_provider(source: str) -> str:
    return replace_one(
        source,
        'val opt = request.credentialOptions.first() as GetPublicKeyCredentialOption',
        'val opt = request.credentialOptions.filterIsInstance<GetPublicKeyCredentialOption>().first()',
        'select passkey option, not password option',
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path, help='root of cloned Keyguard project')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    work = [
        ('CredentialProviderGetRequestHandler.kt', modify_handler),
        ('PasskeyGetActivity.kt', modify_get),
        ('PasskeyProviderGetRequest.kt', modify_provider),
    ]
    result = []
    for filename, transform in work:
        path = args.source / ROOT / filename
        if not path.exists():
            raise SystemExit(f'Expected upstream source missing: {path}')
        before = path.read_text(encoding='utf-8')
        if SENTINEL in before:
            raise SystemExit(f'Patch already applied to {path}; refusing a second application.')
        after = transform(before)
        result.append((path, after))
    # Atomic-ish: write only once every anchor check has passed.
    if not args.dry_run:
        for path, content in result:
            path.write_text(content, encoding='utf-8')
    print('HyperOS unlock-first patch anchors passed (Keyguard noneRelease).')


if __name__ == '__main__':
    main()