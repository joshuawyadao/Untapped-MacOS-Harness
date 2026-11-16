import Foundation
import Security

private let service = "local.untapped.sts2.harness.login"
private let account = "remembered-session-v1"
private let limit = 64 * 1024
private let storedLimit = 60 * 1024

private enum HelperFailure: Error {
    case invalidRequest
    case denied
    case unavailable
}

private func input() throws -> [String: Any] {
    var data = Data()
    while true {
        let chunk = FileHandle.standardInput.readData(ofLength: 4096)
        if chunk.isEmpty { break }
        guard data.count <= limit - chunk.count else { throw HelperFailure.invalidRequest }
        data.append(chunk)
    }
    guard !data.isEmpty,
          let object = try? JSONSerialization.jsonObject(with: data),
          let request = object as? [String: Any] else {
        throw HelperFailure.invalidRequest
    }
    return request
}

private func output(_ object: [String: Any]) {
    guard let data = try? JSONSerialization.data(withJSONObject: object), data.count <= limit else { return }
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([10]))
}

private func baseQuery() -> [String: Any] {
    [kSecClass as String: kSecClassGenericPassword,
     kSecAttrService as String: service,
     kSecAttrAccount as String: account]
}

private func checked(_ status: OSStatus) throws {
    guard status == errSecSuccess else {
        if status == errSecAuthFailed || status == errSecInteractionNotAllowed || status == errSecUserCanceled {
            throw HelperFailure.denied
        }
        throw HelperFailure.unavailable
    }
}

private func load() throws -> [String: Any] {
    var query = baseQuery()
    query[kSecReturnData as String] = true
    query[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    if status == errSecItemNotFound { return [:] }
    try checked(status)
    guard let data = result as? Data, data.count <= storedLimit,
          let object = try? JSONSerialization.jsonObject(with: data),
          let value = object as? [String: Any] else {
        throw HelperFailure.unavailable
    }
    return value
}

private func save(_ value: [String: Any]) throws {
    guard JSONSerialization.isValidJSONObject(value),
          let data = try? JSONSerialization.data(withJSONObject: value),
          data.count <= storedLimit else {
        throw HelperFailure.invalidRequest
    }
    let changes: [String: Any] = [kSecValueData as String: data,
                                   kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlocked]
    let status = SecItemUpdate(baseQuery() as CFDictionary, changes as CFDictionary)
    if status == errSecItemNotFound {
        var item = baseQuery()
        item.merge(changes) { _, new in new }
        try checked(SecItemAdd(item as CFDictionary, nil))
    } else {
        try checked(status)
    }
}

private func clear() throws {
    let status = SecItemDelete(baseQuery() as CFDictionary)
    if status != errSecItemNotFound { try checked(status) }
}

private func run() throws {
    guard CommandLine.arguments.count == 2,
          ["load", "save", "clear"].contains(CommandLine.arguments[1]) else {
        throw HelperFailure.invalidRequest
    }
    let request = try input()
    switch CommandLine.arguments[1] {
    case "load":
        guard request.isEmpty else { throw HelperFailure.invalidRequest }
        output(["value": try load()])
    case "save":
        guard request.count == 1, let value = request["value"] as? [String: Any] else {
            throw HelperFailure.invalidRequest
        }
        try save(value)
        output(["success": true])
    default:
        guard request.isEmpty else { throw HelperFailure.invalidRequest }
        try clear()
        output(["success": true])
    }
}

do {
    try run()
} catch {
    let label: String
    switch error {
    case HelperFailure.invalidRequest: label = "Invalid request"
    case HelperFailure.denied: label = "Keychain access denied"
    default: label = "Keychain unavailable"
    }
    output(["error": label])
    exit(1)
}
