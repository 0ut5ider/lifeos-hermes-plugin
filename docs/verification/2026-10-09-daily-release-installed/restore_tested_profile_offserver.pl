# ABOUTME: Extracts only the synthetic tested profile backup from the completed Proxmox backup snapshot.
# ABOUTME: Uses existing host-local storage authentication without printing or copying credentials.
use strict;
use warnings;
use PVE::Storage;
use PVE::Storage::PBSPlugin;
use PVE::PBSClient;

umask 0077;
my $storeid = 'PBS-01';
my $configuration = PVE::Storage::config();
my $storage = PVE::Storage::storage_config($configuration, $storeid);
my $snapshot = 'ct/101/2026-10-10T03:08:05Z';
my $path = '/root.pxar.didx/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7/application-tested-profile-backup';
my $target = '/var/tmp/lifeos-text-profile-restore-20261010';
die "The restore target already exists\n" if -e $target;
my @parameters = ('extract', $snapshot, $path, $target,
    '--repository', PVE::PBSClient::get_repository($storage));
my $keyfile = PVE::Storage::PBSPlugin::pbs_encryption_key_file_name($storage, $storeid);
if (-f $keyfile) {
    push @parameters, '--crypt-mode', 'encrypt', '--keyfile', $keyfile;
} else {
    push @parameters, '--crypt-mode', 'none';
}
push @parameters, '--ns', $storage->{namespace} if defined $storage->{namespace};
$ENV{PBS_PASSWORD} = PVE::Storage::PBSPlugin::pbs_get_password($storage, $storeid);
$ENV{PBS_FINGERPRINT} = $storage->{fingerprint};
exec '/usr/bin/proxmox-file-restore', @parameters;
die "Cannot start the native extractor: $!\n";
