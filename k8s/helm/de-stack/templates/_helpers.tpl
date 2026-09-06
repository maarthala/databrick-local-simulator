{{/* Common labels applied to every object */}}
{{- define "de-stack.labels" -}}
app.kubernetes.io/part-of: de-stack
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* Selector labels for a component; call with (dict "app" "<name>") */}}
{{- define "de-stack.selector" -}}
app.kubernetes.io/name: {{ .app }}
app.kubernetes.io/part-of: de-stack
{{- end -}}

{{/* Full image ref for a custom (registry-hosted) image; call with (dict "root" $ "repo" .Values.spark.repo "tag" .Values.spark.tag) */}}
{{- define "de-stack.image" -}}
{{- printf "%s/%s:%s" .root.Values.global.imageRegistry .repo .tag -}}
{{- end -}}

{{/* git-sync init container — one-time initial clone so the repo exists before the app starts. Pass root context. */}}
{{- define "de-stack.gitsync.init" -}}
- name: git-sync-init
  image: {{ .Values.git.image }}
  args:
    - --repo={{ .Values.git.repoUrl }}
    - --ref={{ .Values.git.branch }}
    - --root=/git
    - --link=repo
    - --one-time
    - --username={{ .Values.git.username }}
    - --password-file=/etc/git-secret/token
  volumeMounts:
    - { name: git-repo, mountPath: /git }
    - { name: git-token, mountPath: /etc/git-secret, readOnly: true }
{{- end -}}

{{/* git-sync sidecar — keeps the repo up to date. Pass root context. */}}
{{- define "de-stack.gitsync.sidecar" -}}
- name: git-sync
  image: {{ .Values.git.image }}
  args:
    - --repo={{ .Values.git.repoUrl }}
    - --ref={{ .Values.git.branch }}
    - --root=/git
    - --link=repo
    - --period={{ .Values.git.syncPeriodSeconds }}s
    - --username={{ .Values.git.username }}
    - --password-file=/etc/git-secret/token
  volumeMounts:
    - { name: git-repo, mountPath: /git }
    - { name: git-token, mountPath: /etc/git-secret, readOnly: true }
{{- end -}}

{{/* git-sync shared volumes (repo worktree + read-only HTTPS token). Pass root context. */}}
{{- define "de-stack.gitsync.volumes" -}}
- name: git-repo
  emptyDir: {}
- name: git-token
  secret:
    secretName: {{ .Values.git.tokenSecret }}
    # 0444 so the non-root git-sync user (uid 65533) can read it; secret files are
    # root-owned, and the volume is only visible inside this pod.
    defaultMode: 0444
{{- end -}}
