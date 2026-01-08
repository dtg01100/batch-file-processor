// Connection types
export const CONNECTION_TYPES = {
  LOCAL: 'local',
  SMB: 'smb',
  SFTP: 'sftp',
  FTP: 'ftp',
}

// Connection type labels
export const CONNECTION_TYPE_LABELS = {
  [CONNECTION_TYPES.LOCAL]: 'Local',
  [CONNECTION_TYPES.SMB]: 'SMB (Windows Share)',
  [CONNECTION_TYPES.SFTP]: 'SFTP (SSH)',
  [CONNECTION_TYPES.FTP]: 'FTP',
}

// Connection form fields by type
export const CONNECTION_FIELDS = {
  [CONNECTION_TYPES.LOCAL]: [
    { name: 'path', label: 'Path', type: 'text', placeholder: '/path/to/folder' },
  ],
  [CONNECTION_TYPES.SMB]: [
    { name: 'host', label: 'Host', type: 'text', placeholder: 'server.example.com' },
    { name: 'share', label: 'Share', type: 'text', placeholder: 'share-name' },
    { name: 'username', label: 'Username', type: 'text', placeholder: 'username' },
    { name: 'password', label: 'Password', type: 'password', placeholder: 'Password' },
    { name: 'port', label: 'Port', type: 'number', placeholder: '445', default: 445 },
  ],
  [CONNECTION_TYPES.SFTP]: [
    { name: 'host', label: 'Host', type: 'text', placeholder: 'server.example.com' },
    { name: 'username', label: 'Username', type: 'text', placeholder: 'username' },
    { name: 'password', label: 'Password', type: 'password', placeholder: 'Password' },
    { name: 'port', label: 'Port', type: 'number', placeholder: '22', default: 22 },
  ],
  [CONNECTION_TYPES.FTP]: [
    { name: 'host', label: 'Host', type: 'text', placeholder: 'ftp.example.com' },
    { name: 'username', label: 'Username', type: 'text', placeholder: 'username' },
    { name: 'password', label: 'Password', type: 'password', placeholder: 'Password' },
    { name: 'port', label: 'Port', type: 'number', placeholder: '21', default: 21 },
    { name: 'use_tls', label: 'Use TLS', type: 'checkbox', default: true },
  ],
}

// Job status
export const JOB_STATUS = {
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
}

// Run status
export const RUN_STATUS = {
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
}
