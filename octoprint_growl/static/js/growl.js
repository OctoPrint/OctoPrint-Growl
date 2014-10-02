$(function() {
    function GrowlViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self.browsingEnabled = ko.observable(true);

        self.testActive = ko.observable(false);
        self.testResult = ko.observable(false);
        self.testSuccessful = ko.observable(false);
        self.testMessage = ko.observable();

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "growlHosts",
            {
                "name": function(a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            10
        );

        self.chooseInstance = function(data) {
            self.settings.plugins.growl.hostname(data.host);
            self.settings.plugins.growl.port(data.port);
            self.settings.plugins.growl.password("");
        };

        self.testConfiguration = function() {
            self.testActive(true);
            self.testResult(false);
            self.testSuccessful(false);
            self.testMessage("");

            var host = self.settings.plugins.growl.hostname();
            var port = self.settings.plugins.growl.port();
            var pass = self.settings.plugins.growl.password();

            var payload = {
                command: "test",
                host: host,
                port: port,
                password: pass
            };

            $.ajax({
                url: API_BASEURL + "plugin/growl",
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    self.testResult(true);
                    self.testSuccessful(response.success);
                    if (!response.success && response.hasOwnProperty("msg")) {
                        self.testMessage(response.msg);
                    } else {
                        self.testMessage(undefined);
                    }
                },
                complete: function() {
                    self.testActive(false);
                }
            });
        };

        self.fromResponse = function(response) {
            self.browsingEnabled(response.browsing_enabled);

            if (response.browsing_enabled) {
                self.listHelper.updateItems(response.growl_instances);
            } else {
                self.listHelper.updateItems([]);
            }
        };

        self.requestData = function () {
            $.ajax({
                url: API_BASEURL + "plugin/growl",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([GrowlViewModel, ["loginStateViewModel", "settingsViewModel"], document.getElementById("settings_plugin_growl_dialog")]);
});