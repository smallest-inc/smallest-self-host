{{- define "electron.labels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: electron
app.kubernetes.io/version: {{ include "electron.version" . | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}

{{- define "electron.selector" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end }}

{{- define "electron.pullSecrets" -}}
{{- if or .Values.global.imageCredentialsSecretRef .Values.global.imageCredentials.create }}
imagePullSecrets:
  - name: {{ .Values.global.imageCredentialsSecretRef | default (printf "%s-registry" .Release.Name) }}
{{- end }}
{{- end }}

{{- define "electron.licenseSecret" -}}
{{- .Values.global.licenseKeySecretRef | default (printf "%s-license" .Release.Name) }}
{{- end }}

{{- define "electron.keysSecret" -}}
{{- .Values.keysSecretRef | default (printf "%s-keys" .Release.Name) }}
{{- end }}

{{- define "electron.licenseProxyURL" -}}
http://{{ .Release.Name }}-license-proxy:6699
{{- end }}

{{- define "electron.release" -}}
{{- $r := .Files.Get "release.json" | fromJson -}}
{{- if not $r.version }}{{ fail "release.json is missing: install a published Electron chart" }}{{ end -}}
{{- toJson $r -}}
{{- end }}

{{- define "electron.version" -}}
{{- (include "electron.release" . | fromJson).version -}}
{{- end }}

{{- define "electron.initImage" -}}
{{- with .Values.images.registry }}{{ trimSuffix "/" . }}/{{ base $.Values.images.init }}{{ else }}{{ .Values.images.init }}{{ end -}}
{{- end }}

{{- define "electron.image" -}}
{{- $ref := index (include "electron.release" .root | fromJson).images .name -}}
{{- with .root.Values.images.registry }}{{ trimSuffix "/" . }}/{{ base $ref }}{{ else }}{{ $ref }}{{ end -}}
{{- end }}

{{- define "electron.modelRAM" -}}
{{- $gpu := .Values.engines.gpu | upper -}}
{{- if contains "GH200" $gpu -}}{{ fail "engines.gpu GH200: Grace Hopper is an Arm host the images don't run on" }}
{{- else if contains "RTX PRO 6000" $gpu -}}22Gi
{{- else if or (contains "H100" $gpu) (contains "H200" $gpu) -}}34Gi
{{- else -}}{{ fail (printf "engines.gpu %q: Electron runs on H100, H200 or RTX PRO 6000" .Values.engines.gpu) }}
{{- end -}}
{{- end }}

{{- define "electron.podLabels" -}}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/part-of: electron
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/name: {{ .name }}
{{- end }}
