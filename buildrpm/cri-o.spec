
%global debug_package   %{nil}
%global _find_debuginfo_dwz_opts %{nil}
%global _dwz_low_mem_die_limit 0

%global import_path github.com/cri-o/cri-o
%global service_name crio
%global _buildhost build-ol%{?oraclelinux}-%{?_arch}.oracle.com

Name: cri-o
Version: 1.33.10
Release: 1%{?dist}
ExcludeArch: ppc64
Summary: Kubernetes Container Runtime Interface for OCI-based containers
License: ASL 2.0
URL: https://%{import_path}
Vendor:  Oracle America
Source0: %{name}-%{version}.tar.bz2
Source3: %{service_name}-network.sysconfig
Source4: %{service_name}-storage.sysconfig
Source5: %{service_name}-metrics.sysconfig
Patch0: ocr-workaround.patch.txt
BuildRequires: golang
BuildRequires: btrfs-progs-devel
BuildRequires: device-mapper-devel
BuildRequires: git
BuildRequires: glib2-devel
BuildRequires: glibc-static
BuildRequires: gpgme-devel
BuildRequires: libassuan-devel
BuildRequires: libseccomp-devel
BuildRequires: pkgconfig(systemd)
BuildRequires: make
Requires(pre): container-selinux
Requires: %{_sysconfdir}/cri-tools/1.33
Requires: containers-common >= 1:0.1.31-14
Requires: runc >= 1.0.2
Obsoletes: ocid <= 0.3
Provides: ocid = %{version}-%{release}
Provides: %{service_name} = %{version}-%{release}
Provides: %{_sysconfdir}/crio/1.33
Requires: containernetworking-plugins

#TODO: Remove pinning down of conmon-3:2.0.21-1 version when conmon moves to 2.1.x
Requires: conmon >= 3:2.1.3-8%{?dist}
Requires: socat

%description
CRI-O is meant to provide an integration path between OCI conformant runtimes and the kubelet. Specifically, it implements the Kubelet Container Runtime Interface (CRI) using OCI conformant runtimes.

%prep
%setup -q -n %{name}-%{version}

# process the patches
%patch0

project_dir=$(pwd)
mkdir -p src/github.com/cri-o/cri-o
mkdir -p src/k8s.io/kubernetes
mv $(ls | grep -v "^src$") src/github.com/cri-o/cri-o/.

%build
export GOPATH=$(pwd)
pushd src/github.com/cri-o/cri-o
make GIT_TREE_STATE=clean TRIMPATH="-trimpath=false" EXTRA_LDFLAGS="-X main.VERSION=v%{version}" all
popd

%install
export GOPATH=$(pwd)
pushd src/github.com/cri-o/cri-o

# Create a version file so this project can be bounded as a dependency
install -dp %{buildroot}%{_sysconfdir}/crio
touch %{buildroot}%{_sysconfdir}/crio/1.33

# Edit the crio and crio-wipe unit file to have to correct binary location on the system
sed -i 's/\/local//' contrib/systemd/crio.service
sed -i 's/\/local//' contrib/systemd/crio-wipe.service

# install binaries
install -dp %{buildroot}{%{_bindir},%{_libexecdir}/%{service_name}}
install -p -m 755 bin/%{service_name} %{buildroot}%{_bindir}

# install conf files
install -dp %{buildroot}%{_sysconfdir}/cni/net.d
install -p -m 644 contrib/cni/10-crio-bridge.conflist %{buildroot}%{_sysconfdir}/cni/net.d/100-crio-bridge.conf
install -p -m 644 contrib/cni/99-loopback.conflist %{buildroot}%{_sysconfdir}/cni/net.d/200-loopback.conf

install -dp %{buildroot}%{_sysconfdir}/sysconfig
install -p -m 644 contrib/sysconfig/%{service_name} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}
install -p -m 644 %{SOURCE3} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}-network
install -p -m 644 %{SOURCE4} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}-storage
install -p -m 644 %{SOURCE5} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}-metrics

make PREFIX=%{buildroot}%{_usr} \
            DESTDIR=%{buildroot} \
            install.bin \
            install.completions \
            install.config \
            install.man \
            install.systemd

./bin/%{service_name} \
      --selinux \
      --cgroup-manager "cgroupfs" \
      --conmon "/usr/bin/conmon" \
      --cni-plugin-dir "/opt/cni/bin" \
      config > %{service_name}.conf

install -p -m 644 %{service_name}.conf %{buildroot}%{_sysconfdir}/%{service_name}/%{service_name}.conf
popd
mv src/github.com/cri-o/cri-o/*.md .
mv src/github.com/cri-o/cri-o/LICENSE .
mv src/github.com/cri-o/cri-o/THIRD_PARTY_LICENSES.txt .

%post
%systemd_post %{service_name}

%preun
%systemd_preun %{service_name}

%postun
%systemd_postun_with_restart %{service_name}

%files
%license LICENSE THIRD_PARTY_LICENSES.txt
%{_sysconfdir}/crio/1.33
%doc README.md
%{_bindir}/%{service_name}
%{_bindir}/pinns
%{_mandir}/man5/%{service_name}*.5*
%{_mandir}/man8/%{service_name}*.8*
%dir %{_sysconfdir}/%{service_name}
%config(noreplace) %{_sysconfdir}/%{service_name}/%{service_name}.conf
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}-storage
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}-network
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}-metrics
%config(noreplace) %{_sysconfdir}/cni/net.d/100-%{service_name}-bridge.conf
%config(noreplace) %{_sysconfdir}/cni/net.d/200-loopback.conf
%config(noreplace) %{_sysconfdir}/crictl.yaml

/usr/share/bash-completion/completions/crio
/usr/share/fish/completions/crio.fish
/usr/share/zsh/site-functions/_crio
%dir %{_libexecdir}/%{service_name}
%{_unitdir}/%{service_name}.service
%{_unitdir}/%{service_name}-wipe.service
%dir %{_datadir}/oci-umount
%dir %{_datadir}/oci-umount/oci-umount.d
%{_datadir}/oci-umount/oci-umount.d/%{service_name}-umount.conf
#crio hook dir
%dir %{_datadir}/containers/oci/hooks.d

%changelog
* Tue Mar 03 2026 Oracle Cloud Native Environment Authors <noreply@oracle.com> - 1.33.10-1
- Added Oracle Specifile Files for cri-o
