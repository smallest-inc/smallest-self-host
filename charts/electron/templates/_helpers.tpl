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
http://{{ .Release.Name }}-license-proxy:8090
{{- end }}

{{/* What this chart's release runs (release.json, written when the chart is published): its version,
its images by digest, and a fingerprint of each GPU family's model and vLLM settings. */}}
{{- define "electron.release" -}}
{{- $r := .Files.Get "release.json" | fromJson -}}
{{- if not $r.version }}{{ fail "release.json is missing: install a published Electron chart" }}{{ end -}}
{{- toJson $r -}}
{{- end }}

{{- define "electron.version" -}}
{{- (include "electron.release" . | fromJson).version -}}
{{- end }}

{{/* The router's init image, from images.registry when it is set, like every other image. */}}
{{- define "electron.initImage" -}}
{{- with .Values.images.registry }}{{ trimSuffix "/" . }}/{{ base $.Values.images.init }}{{ else }}{{ .Values.images.init }}{{ end -}}
{{- end }}

{{/* An image as released, or from images.registry with the same name, tag and digest. */}}
{{- define "electron.image" -}}
{{- $ref := index (include "electron.release" .root | fromJson).images .name -}}
{{- with .root.Values.images.registry }}{{ trimSuffix "/" . }}/{{ base $ref }}{{ else }}{{ $ref }}{{ end -}}
{{- end }}

{{/* The engines' GPU family: the build the license server hands them. */}}
{{- define "electron.family" -}}
{{- $gpu := .Values.engines.gpu | upper -}}
{{- if contains "GH200" $gpu -}}{{ fail "engines.gpu GH200: Grace Hopper is an Arm host the images don't run on" }}
{{- else if contains "RTX PRO 6000" $gpu -}}rtx
{{- else if or (contains "H100" $gpu) (contains "H200" $gpu) -}}hopper
{{- else -}}{{ fail (printf "engines.gpu %q: Electron runs on H100, H200 or RTX PRO 6000" .Values.engines.gpu) }}
{{- end -}}
{{- end }}

{{/* The model's decrypted size in RAM while it loads, by GPU type. */}}
{{- define "electron.modelRAM" -}}
{{- $gpu := .Values.engines.gpu | upper -}}
{{- if contains "RTX PRO 6000" $gpu -}}22Gi
{{- else if or (contains "H100" $gpu) (contains "H200" $gpu) -}}34Gi
{{- else -}}{{ fail (printf "engines.gpu %q: Electron runs on H100, H200 or RTX PRO 6000" .Values.engines.gpu) }}
{{- end -}}
{{- end }}

{{/* No version or chart labels on pods: a release restarts only the pods whose image, build or keys
it changes. */}}
{{- define "electron.podLabels" -}}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/part-of: electron
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/name: {{ .name }}
{{- end }}
