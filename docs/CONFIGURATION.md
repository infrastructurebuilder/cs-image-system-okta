# Configuring the Okta plugin

What a configuration tree writes for the Okta identity plugin: its group
builders and user builders in `cfg/group-builders.yml`. This page is the one
source for these fields (they moved here from cs-image-system-3's
[configuration reference](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/CONFIGURATION.md), section 9, with the
plugin, spec 008); everything else a tree writes, including the fields every
builder shares, is that reference's.

Keys: `group_builders` and `user_builders`. Models:
[`okta_tf_models.py`](../packages/okta-opa-plugin/src/cs_image_system/okta_opa_plugin/okta_tf_models.py),
[`okta_tf_workspace.py`](../packages/okta-opa-plugin/src/cs_image_system/okta_opa_plugin/okta_tf_workspace.py),
and the kit's
[`group_builder.py`](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/packages/base/src/cs_image_system/base/models/group_builder.py) and
[`user_builder.py`](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/packages/base/src/cs_image_system/base/models/user_builder.py).

## 1. The Okta terraform workspace (shared by group and user builders)

`OktaTfWorkspaceModelMixin`. Each builder owns one terraform root.

| Field | Type | Default | Meaning and allowed values |
| --- | --- | --- | --- |
| `org` | str | required | the Okta org name; `okta` provider `org_name` |
| `team` | str | required | the OPA team; also names the credential variables (below) |
| `key` | EncryptedStr | `default` | the oktapam API key. Left at default it becomes `var.<team>_key`, filled from `TF_VAR_<team>_key`; a literal may be `ENC[age:…]` and is then emitted by reference |
| `secret` | EncryptedStr | `default` | likewise, `TF_VAR_<team>_secret` |
| `api_host` | str | `https://{{ this.org }}.pam.okta.com` | the OPA API host |
| `okta_base_url` | str | `okta.com` | `okta` provider `base_url` (`oktapreview.com` for a preview org) |
| `default_user_status` | str | `STAGED` | `okta_user.status` for enabled managed users: `ACTIVE`, `STAGED`, `SUSPENDED`, `DEPROVISIONED`; disabled users are always `SUSPENDED`. Not validated here: another value is emitted as written and refused by the provider |
| `required_providers` | list | `[]` | `{name (required), version (required), source, config}`; `oktapam` gets its credentials wired through variables, `okta` reads `OKTA_API_*` from the environment and its `config` may carry any provider argument |
| `state_configuration` | str | `default` | the state backend of the identity roots; `default` takes the default backend (an identity root has no runtime to inherit from) |

`<team>` in a variable name is the team with every non-alphanumeric
character replaced by `_` (`nos-coastal-modeling-cloud-sandbox` →
`nos_coastal_modeling_cloud_sandbox`).

## 2. Group builders

`OktaGroupBuilderModel`; types `okta-tf` (managed OPA groups) and
`okta-tf-ro` (lookups of existing Okta groups only). The fields every
builder shares ([the configuration reference, 4.1](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/CONFIGURATION.md#41-fields-common-to-every-builder))
and section 1 plus:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `gateway_selector` | str or null | null | the resource-group project's `gateway_selector`; falls back to `config.okta_gateway_selector` |
| `workload_connection` | str or null | null | the team's workload connection, by name, made by hand once ([CI_SETUP.md section 3.5](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/examples/_skeleton/CI_SETUP.md#35-okta-and-okta-privileged-access)); with `workload_role` it makes the builder keep one CI login policy per managed group |
| `workload_role` | str or null | null | the team's workload role, by name; the only principal of every CI login policy |
| `account_discovery` | bool | `true` | the project's `account_discovery` |
| `posix` | str | **required** on `okta-tf`, no default | a `type: posix` group builder that makes these groups exist on their machines (created after each applying run with OPA's gid; members join at each login through a baked PAM hook), or `none` for no posix configuration (`validate` and the state query note what that keeps off the machines). Absent, empty, an undeclared name or a non-posix builder is refused at `validate`. Not read by `okta-tf-ro` |
| `posix_ssh_keys` | bool | `false` | opt-in: the login hook also installs each member's declared `public_keys:` as their `authorized_keys` |

For every managed group `<g>` the `okta-tf` builder emits: the `oktapam`
groups `<g>_user` and `<g>_admin`; the resource group `<g>_rg`, delegated
to `<g>_admin` (and to the root group's admin group when the group keeps
`include_root_group_in_admins`); the project `<g>_rg_login` with the
gateway selector and account discovery; two security policies (user and
admin) that select servers by the labels `system.os_type = linux` and
`sftd.tx.group = <g>`; and one `oktapam_user_group_attachment` per member
and per admin, whose `username` is the user's `name`. Base images that
declare `identity_types: [okta]` get the OPA server agent baked, dormant;
an instance image activates it for its owning group. The identity type
token is `okta`.

## 3. User builders

`UserBuilderModel` and `OktaUserBuilderModel`; types `okta-tf` (managed:
an `okta_user` resource plus a lookup) and `okta-tf-ro` (lookup only;
`managed: true` on a user is refused). The fields every builder shares and
section 1 plus:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `default_user_email_template` | str | `{{ user.name }}` | the email of a user that declares none; `user` is the user being rendered |
| `default_user_description_template` | str | `User {{ user.name }} / {{ user.email }}` | the description of a user that declares none |
| `email_as_username` | bool | `true` | when true a user's `name` must equal its `email` (case-insensitive); a blank name is set from the email; a mismatch aborts the load |
| `email_domain` | str | none | the fragment `default_user_email_template` renders with (`{{ builder.email_domain }}`); the value that is encrypted in the live tree, so a derived address carries the ciphertext ([the configuration reference, 13](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/CONFIGURATION.md#13-encrypted-values)) |

The Okta login of an emitted user is its email. Lookups search
`profile.login` by that email and skip roles and groups.

## 4. Example

[`cfg/group-builders.yml`](../tests/instance/fixture/cfg/group-builders.yml)
of the instance suite's fixture, in short:

```yaml
---
group_builders:
  - name: oktagroups
    is_default: true
    type: okta-tf
    executable: open-tofu-1
    org: "noaa"
    team: "nos-coastal-modeling-cloud-sandbox"
    posix: posix-local
    required_providers:
      - name: oktapam
        source: okta/oktapam
        version: '>= 0.6.3'
  - name: posix-local
    type: posix
user_builders:
  - name: okta-tf-users
    is_default: true
    type: okta-tf-ro
    executable: open-tofu-1
    org: "noaa"
    team: "nos-coastal-modeling-cloud-sandbox"
    email_as_username: false
    default_user_email_template: "{{ user.name }}@example.invalid"
    required_providers:
      - name: okta
        source: okta/okta
        version: '>= 6.0'
```
