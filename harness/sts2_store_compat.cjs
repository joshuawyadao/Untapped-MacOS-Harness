function resolveHarnessSts2LocalFileIo(saveStore) {
  const godotFileIoClass = 'MegaCrit.Sts2.Core.Saves.GodotFileIo';
  const saveStoreClassName = saveStore.className;
  if (saveStoreClassName === godotFileIoClass) {
    return saveStore.cast(GodotFileIo);
  }
  if (saveStoreClassName === 'MegaCrit.Sts2.Core.Saves.CloudSaveStore') {
    const localStore = new ScryObject(saveStore.object('LocalStore'));
    if (localStore.className !== godotFileIoClass) {
      throw new ScryError('Unsupported STS2 save store');
    }
    return localStore.cast(GodotFileIo);
  }
  throw new ScryError('Unsupported STS2 save store');
}
